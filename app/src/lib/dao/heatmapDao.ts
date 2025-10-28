import { db } from "@/lib/db";
import { sql } from "kysely";

export interface HeatmapMinuteRecord {
	id: number;
	camera_id: string;
	timestamp: Date;
	video_path: string;
	height: number;
	width: number;
	downscale_factor: number;
	intensity_array: Buffer;
	frame_count: number;
	total_intensity: number;
	max_intensity: number;
	nonzero_pixels: number;
	processed_at: Date;
}

export interface AggregatedHeatmapData {
	height: number;
	width: number;
	records: HeatmapMinuteRecord[];
	totalMinutes: number;
}

export class HeatmapDao {
	/**
	 * Fetch heatmap minute records for a specific camera and date range.
	 */
	async getHeatmapMinutes(
		cameraId: string,
		startDate: Date,
		endDate: Date
	): Promise<HeatmapMinuteRecord[]> {
		const results = await db
			.selectFrom("heatmap_minutes")
			.selectAll()
			.where("camera_id", "=", cameraId)
			.where("timestamp", ">=", startDate)
			.where("timestamp", "<", endDate)
			.orderBy("timestamp", "asc")
			.execute();

		return results.map((row) => ({
			id: row.id,
			camera_id: row.camera_id,
			timestamp: new Date(row.timestamp),
			video_path: row.video_path,
			height: row.height,
			width: row.width,
			downscale_factor: row.downscale_factor,
			intensity_array: row.intensity_array as Buffer,
			frame_count: row.frame_count,
			total_intensity: Number(row.total_intensity),
			max_intensity: Number(row.max_intensity),
			nonzero_pixels: row.nonzero_pixels,
			processed_at: new Date(row.processed_at),
		}));
	}

	/**
	 * Get aggregated heatmap data for a camera and date.
	 * Returns all records with metadata needed for image generation.
	 */
	async getAggregatedHeatmapData(
		cameraId: string,
		date: string
	): Promise<AggregatedHeatmapData | null> {
		// Parse date and create date range for full day
		const startDate = new Date(date);
		startDate.setHours(0, 0, 0, 0);

		const endDate = new Date(date);
		endDate.setHours(23, 59, 59, 999);

		const records = await this.getHeatmapMinutes(cameraId, startDate, endDate);

		if (records.length === 0) {
			return null;
		}

		// All records should have same dimensions
		const { height, width } = records[0];

		return {
			height,
			width,
			records,
			totalMinutes: records.length,
		};
	}

	/**
	 * Check if heatmap data exists for a specific camera and date.
	 */
	async hasHeatmapData(cameraId: string, date: string): Promise<boolean> {
		const startDate = new Date(date);
		startDate.setHours(0, 0, 0, 0);

		const endDate = new Date(date);
		endDate.setHours(23, 59, 59, 999);

		const result = await db
			.selectFrom("heatmap_minutes")
			.select((eb) => eb.fn.count("id").as("count"))
			.where("camera_id", "=", cameraId)
			.where("timestamp", ">=", startDate)
			.where("timestamp", "<", endDate)
			.executeTakeFirst();

		return result ? Number(result.count) > 0 : false;
	}
}
