import { NextRequest, NextResponse } from "next/server";
import { HeatmapDao } from "@/lib/dao/heatmapDao";
import { generateHeatmapImage } from "@/lib/services/heatmapImageGenerator";

export async function GET(request: NextRequest) {
	const searchParams = request.nextUrl.searchParams;
	const cameraId = searchParams.get("camera_id");
	const date = searchParams.get("date");

	console.log("Image request:", { cameraId, date });

	if (!cameraId || !date) {
		return NextResponse.json(
			{ error: "camera_id and date required" },
			{ status: 400 }
		);
	}

	try {
		// Fetch heatmap data from database
		const dao = new HeatmapDao();
		const heatmapData = await dao.getAggregatedHeatmapData(cameraId, date);

		if (!heatmapData) {
			console.log("No data found for:", { cameraId, date });
			return NextResponse.json(
				{ error: "No data found for this date" },
				{ status: 404 }
			);
		}

		console.log(
			`Generating heatmap from ${heatmapData.totalMinutes} minutes of data...`
		);

		// Generate image buffer
		const imageBuffer = await generateHeatmapImage(heatmapData, {
			quality: 90,
		});

		console.log(`Image generated successfully: ${imageBuffer.length} bytes`);

		// Return the image directly
		// Convert Buffer to Uint8Array for web-compatible response
		return new NextResponse(new Uint8Array(imageBuffer), {
			headers: {
				"Content-Type": "image/jpeg",
				"Cache-Control": "public, max-age=3600",
			},
		});
	} catch (error) {
		console.error("Error generating heatmap:", error);
		console.error(
			"Error details:",
			error instanceof Error ? error.message : String(error)
		);
		return NextResponse.json(
			{
				error: "Failed to generate image",
				details: error instanceof Error ? error.message : String(error),
			},
			{ status: 500 }
		);
	}
}
