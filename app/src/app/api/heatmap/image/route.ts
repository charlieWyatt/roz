import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import { readFile, unlink } from "fs/promises";
import path from "path";

const execAsync = promisify(exec);

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
		// Check if data exists for this date
		const startDate = new Date(date);
		const endDate = new Date(startDate);
		endDate.setDate(endDate.getDate() + 1);

		console.log("Checking data for:", { cameraId, date });

		const count = await db
			.selectFrom("heatmap_minutes")
			.select((eb) => eb.fn.count("id").as("count"))
			.where("camera_id", "=", cameraId)
			.where("timestamp", ">=", startDate)
			.where("timestamp", "<", endDate)
			.executeTakeFirst();

		if (!count || Number(count.count) === 0) {
			return NextResponse.json({ error: "No data found" }, { status: 404 });
		}

		console.log(`Found ${count.count} minutes, generating image...`);

		// Generate temporary output path
		const tempFile = path.join(
			"/tmp",
			`heatmap_${cameraId}_${date}_${Date.now()}.jpg`
		);

		// Call Python script to generate heatmap
		const projectRoot = path.join(process.cwd(), "..");
		const pythonScript = path.join(
			projectRoot,
			"analytics/generate_heatmap_image.py"
		);

		const command = `cd ${projectRoot} && poetry run python ${pythonScript} --date "${date}" --camera-id "${cameraId}" --output "${tempFile}"`;

		console.log("Running command:", command);

		await execAsync(command);

		// Read the generated image
		const imageBuffer = await readFile(tempFile);

		// Clean up temp file
		await unlink(tempFile).catch(() => {});

		console.log("Image generated successfully");

		// Return the image
		return new NextResponse(imageBuffer, {
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
