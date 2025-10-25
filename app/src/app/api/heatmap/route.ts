import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { sql } from "kysely";

export async function GET(request: NextRequest) {
	const searchParams = request.nextUrl.searchParams;
	const cameraId = searchParams.get("camera_id");
	const date = searchParams.get("date"); // YYYY-MM-DD format

	if (!cameraId || !date) {
		return NextResponse.json(
			{ error: "camera_id and date are required" },
			{ status: 400 }
		);
	}

	try {
		// Get all minutes for the selected date
		const startDate = new Date(date);
		const endDate = new Date(startDate);
		endDate.setDate(endDate.getDate() + 1);

		const minutes = await db
			.selectFrom("heatmap_minutes")
			.select([
				"id",
				"timestamp",
				"intensity_array",
				"height",
				"width",
				"total_intensity",
				"max_intensity",
				"frame_count",
			])
			.where("camera_id", "=", cameraId)
			.where("timestamp", ">=", startDate)
			.where("timestamp", "<", endDate)
			.orderBy("timestamp")
			.execute();

		if (minutes.length === 0) {
			return NextResponse.json(
				{ error: "No data found for this date" },
				{ status: 404 }
			);
		}

		// Return metadata (we'll aggregate and render on the server)
		return NextResponse.json({
			camera_id: cameraId,
			date,
			minute_count: minutes.length,
			total_intensity: minutes.reduce((sum, m) => sum + m.total_intensity, 0),
			time_range: {
				start: minutes[0].timestamp,
				end: minutes[minutes.length - 1].timestamp,
			},
			dimensions: {
				height: minutes[0].height,
				width: minutes[0].width,
			},
		});
	} catch (error) {
		console.error("Error fetching heatmap:", error);
		return NextResponse.json(
			{ error: "Failed to fetch heatmap data" },
			{ status: 500 }
		);
	}
}
