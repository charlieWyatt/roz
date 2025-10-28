import { describe, it, expect, beforeEach } from "@jest/globals";
import { deflate } from "zlib";
import { promisify } from "util";
import {
	generateHeatmapImage,
	calculateHeatmapStats,
} from "../heatmapImageGenerator";
import { AggregatedHeatmapData } from "@/lib/dao/heatmapDao";
import sharp from "sharp";

const deflateAsync = promisify(deflate);

describe("HeatmapImageGenerator", () => {
	describe("generateHeatmapImage", () => {
		it("should generate a JPEG image buffer from heatmap data", async () => {
			// Create a simple 2x2 heatmap
			const width = 2;
			const height = 2;
			const heatmapArray = new Float32Array([0, 10, 20, 30]);

			// Compress the array as the database would
			const buffer = Buffer.from(heatmapArray.buffer);
			const compressed = await deflateAsync(buffer);

			const mockData: AggregatedHeatmapData = {
				height,
				width,
				records: [
					{
						id: 1,
						camera_id: "default",
						timestamp: new Date("2025-10-20T14:00:00"),
						video_path: "raw_videos/2025/10/20/14/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed,
						frame_count: 60,
						total_intensity: 60,
						max_intensity: 30,
						nonzero_pixels: 4,
						processed_at: new Date("2025-10-20T14:01:00"),
					},
				],
				totalMinutes: 1,
			};

			const imageBuffer = await generateHeatmapImage(mockData);

			// Verify it's a valid image
			expect(Buffer.isBuffer(imageBuffer)).toBe(true);
			expect(imageBuffer.length).toBeGreaterThan(0);

			// Verify it's a valid JPEG by checking magic bytes
			expect(imageBuffer[0]).toBe(0xff);
			expect(imageBuffer[1]).toBe(0xd8);

			// Verify dimensions using sharp
			const metadata = await sharp(imageBuffer).metadata();
			expect(metadata.width).toBe(width);
			expect(metadata.height).toBe(height);
			expect(metadata.format).toBe("jpeg");
		});

		it("should handle multiple records and aggregate them", async () => {
			const width = 3;
			const height = 3;

			// Create two heatmaps
			const heatmap1 = new Float32Array([1, 2, 3, 4, 5, 6, 7, 8, 9]);
			const heatmap2 = new Float32Array([9, 8, 7, 6, 5, 4, 3, 2, 1]);

			const compressed1 = await deflateAsync(Buffer.from(heatmap1.buffer));
			const compressed2 = await deflateAsync(Buffer.from(heatmap2.buffer));

			const mockData: AggregatedHeatmapData = {
				height,
				width,
				records: [
					{
						id: 1,
						camera_id: "default",
						timestamp: new Date("2025-10-20T14:00:00"),
						video_path: "raw_videos/2025/10/20/14/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed1,
						frame_count: 60,
						total_intensity: 45,
						max_intensity: 9,
						nonzero_pixels: 9,
						processed_at: new Date("2025-10-20T14:01:00"),
					},
					{
						id: 2,
						camera_id: "default",
						timestamp: new Date("2025-10-20T15:00:00"),
						video_path: "raw_videos/2025/10/20/15/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed2,
						frame_count: 60,
						total_intensity: 45,
						max_intensity: 9,
						nonzero_pixels: 9,
						processed_at: new Date("2025-10-20T15:01:00"),
					},
				],
				totalMinutes: 2,
			};

			const imageBuffer = await generateHeatmapImage(mockData);

			expect(Buffer.isBuffer(imageBuffer)).toBe(true);
			expect(imageBuffer.length).toBeGreaterThan(0);

			const metadata = await sharp(imageBuffer).metadata();
			expect(metadata.width).toBe(width);
			expect(metadata.height).toBe(height);
		});

		it("should handle all-zero heatmap gracefully", async () => {
			const width = 2;
			const height = 2;
			const heatmapArray = new Float32Array([0, 0, 0, 0]);

			const compressed = await deflateAsync(Buffer.from(heatmapArray.buffer));

			const mockData: AggregatedHeatmapData = {
				height,
				width,
				records: [
					{
						id: 1,
						camera_id: "default",
						timestamp: new Date("2025-10-20T14:00:00"),
						video_path: "raw_videos/2025/10/20/14/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed,
						frame_count: 60,
						total_intensity: 0,
						max_intensity: 0,
						nonzero_pixels: 0,
						processed_at: new Date("2025-10-20T14:01:00"),
					},
				],
				totalMinutes: 1,
			};

			// Should not throw error
			const imageBuffer = await generateHeatmapImage(mockData);
			expect(Buffer.isBuffer(imageBuffer)).toBe(true);
		});

		it("should respect quality option", async () => {
			const width = 2;
			const height = 2;
			const heatmapArray = new Float32Array([10, 20, 30, 40]);

			const compressed = await deflateAsync(Buffer.from(heatmapArray.buffer));

			const mockData: AggregatedHeatmapData = {
				height,
				width,
				records: [
					{
						id: 1,
						camera_id: "default",
						timestamp: new Date("2025-10-20T14:00:00"),
						video_path: "raw_videos/2025/10/20/14/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed,
						frame_count: 60,
						total_intensity: 100,
						max_intensity: 40,
						nonzero_pixels: 4,
						processed_at: new Date("2025-10-20T14:01:00"),
					},
				],
				totalMinutes: 1,
			};

			const highQuality = await generateHeatmapImage(mockData, { quality: 95 });
			const lowQuality = await generateHeatmapImage(mockData, { quality: 50 });

			// High quality should be larger file size
			expect(highQuality.length).toBeGreaterThan(lowQuality.length);
		});
	});

	describe("calculateHeatmapStats", () => {
		it("should calculate correct statistics", async () => {
			const width = 2;
			const height = 2;
			const heatmap = new Float32Array([1, 2, 3, 4]);
			const compressed = await deflateAsync(Buffer.from(heatmap.buffer));

			const mockData: AggregatedHeatmapData = {
				height,
				width,
				records: [
					{
						id: 1,
						camera_id: "default",
						timestamp: new Date("2025-10-20T14:00:00"),
						video_path: "raw_videos/2025/10/20/14/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed,
						frame_count: 60,
						total_intensity: 1000,
						max_intensity: 50,
						nonzero_pixels: 4,
						processed_at: new Date("2025-10-20T14:01:00"),
					},
					{
						id: 2,
						camera_id: "default",
						timestamp: new Date("2025-10-20T15:00:00"),
						video_path: "raw_videos/2025/10/20/15/clip.mp4",
						height,
						width,
						downscale_factor: 0.25,
						intensity_array: compressed,
						frame_count: 60,
						total_intensity: 2000,
						max_intensity: 75,
						nonzero_pixels: 4,
						processed_at: new Date("2025-10-20T15:01:00"),
					},
				],
				totalMinutes: 2,
			};

			const stats = calculateHeatmapStats(mockData);

			expect(stats.totalMinutes).toBe(2);
			expect(stats.totalIntensity).toBe(3000);
			expect(stats.maxIntensity).toBe(75);
			expect(stats.avgIntensity).toBe(1500);
		});
	});
});
