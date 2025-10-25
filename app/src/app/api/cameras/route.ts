import { db } from "@/lib/db";
import { NextResponse } from "next/server";

export async function GET() {
	try {
		console.log("Fetching cameras from database...");

		// Get distinct camera IDs with their latest activity
		const cameras = await db
			.selectFrom("heatmap_minutes")
			.select([
				"camera_id",
				(eb) => eb.fn.count("id").as("total_minutes"),
				(eb) => eb.fn.max("timestamp").as("latest_activity"),
				(eb) => eb.fn.min("timestamp").as("earliest_activity"),
			])
			.groupBy("camera_id")
			.orderBy("camera_id")
			.execute();

		console.log(`Found ${cameras.length} cameras`);
		return NextResponse.json({ cameras });
	} catch (error) {
		console.error("Error fetching cameras:", error);
		return NextResponse.json(
			{ error: "Failed to fetch cameras", details: String(error) },
			{ status: 500 }
		);
	}
}
