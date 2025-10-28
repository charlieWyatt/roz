import { describe, it, expect, beforeEach, jest } from "@jest/globals";
import { HeatmapDao } from "../heatmapDao";
import { db } from "@/lib/db";

// Mock the database module
jest.mock("@/lib/db");

describe("HeatmapDao", () => {
	let dao: HeatmapDao;

	beforeEach(() => {
		dao = new HeatmapDao();
		jest.clearAllMocks();
	});

	describe("getHeatmapMinutes", () => {
		it("should fetch heatmap minutes for a given date range", async () => {
			const mockData = [
				{
					id: 1,
					camera_id: "default",
					timestamp: new Date("2025-10-20T14:00:00"),
					video_path: "raw_videos/2025/10/20/14/clip.mp4",
					height: 180,
					width: 320,
					downscale_factor: 0.25,
					intensity_array: Buffer.from([1, 2, 3, 4]),
					frame_count: 60,
					total_intensity: 1500,
					max_intensity: 50,
					nonzero_pixels: 100,
					processed_at: new Date("2025-10-20T14:01:00"),
				},
			];

			const mockQuery = {
				selectAll: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				orderBy: jest.fn().mockReturnThis(),
				execute: jest.fn().mockResolvedValue(mockData),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const startDate = new Date("2025-10-20T00:00:00");
			const endDate = new Date("2025-10-20T23:59:59");

			const result = await dao.getHeatmapMinutes("default", startDate, endDate);

			expect(db.selectFrom).toHaveBeenCalledWith("heatmap_minutes");
			expect(mockQuery.where).toHaveBeenCalledWith("camera_id", "=", "default");
			expect(result).toHaveLength(1);
			expect(result[0].camera_id).toBe("default");
			expect(result[0].height).toBe(180);
			expect(result[0].width).toBe(320);
		});

		it("should return empty array when no data exists", async () => {
			const mockQuery = {
				selectAll: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				orderBy: jest.fn().mockReturnThis(),
				execute: jest.fn().mockResolvedValue([]),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.getHeatmapMinutes(
				"default",
				new Date(),
				new Date()
			);

			expect(result).toEqual([]);
		});
	});

	describe("getAggregatedHeatmapData", () => {
		it("should return aggregated data for a valid date", async () => {
			const mockData = [
				{
					id: 1,
					camera_id: "default",
					timestamp: new Date("2025-10-20T14:00:00"),
					video_path: "raw_videos/2025/10/20/14/clip.mp4",
					height: 180,
					width: 320,
					downscale_factor: 0.25,
					intensity_array: Buffer.from([1, 2, 3, 4]),
					frame_count: 60,
					total_intensity: 1500,
					max_intensity: 50,
					nonzero_pixels: 100,
					processed_at: new Date("2025-10-20T14:01:00"),
				},
				{
					id: 2,
					camera_id: "default",
					timestamp: new Date("2025-10-20T15:00:00"),
					video_path: "raw_videos/2025/10/20/15/clip.mp4",
					height: 180,
					width: 320,
					downscale_factor: 0.25,
					intensity_array: Buffer.from([5, 6, 7, 8]),
					frame_count: 60,
					total_intensity: 2000,
					max_intensity: 75,
					nonzero_pixels: 150,
					processed_at: new Date("2025-10-20T15:01:00"),
				},
			];

			const mockQuery = {
				selectAll: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				orderBy: jest.fn().mockReturnThis(),
				execute: jest.fn().mockResolvedValue(mockData),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.getAggregatedHeatmapData(
				"default",
				"2025-10-20"
			);

			expect(result).not.toBeNull();
			expect(result?.totalMinutes).toBe(2);
			expect(result?.height).toBe(180);
			expect(result?.width).toBe(320);
			expect(result?.records).toHaveLength(2);
		});

		it("should return null when no data exists", async () => {
			const mockQuery = {
				selectAll: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				orderBy: jest.fn().mockReturnThis(),
				execute: jest.fn().mockResolvedValue([]),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.getAggregatedHeatmapData(
				"default",
				"2025-10-20"
			);

			expect(result).toBeNull();
		});
	});

	describe("hasHeatmapData", () => {
		it("should return true when data exists", async () => {
			const mockQuery = {
				select: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				executeTakeFirst: jest.fn().mockResolvedValue({ count: "5" }),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.hasHeatmapData("default", "2025-10-20");

			expect(result).toBe(true);
		});

		it("should return false when no data exists", async () => {
			const mockQuery = {
				select: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				executeTakeFirst: jest.fn().mockResolvedValue({ count: "0" }),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.hasHeatmapData("default", "2025-10-20");

			expect(result).toBe(false);
		});

		it("should return false when query returns null", async () => {
			const mockQuery = {
				select: jest.fn().mockReturnThis(),
				where: jest.fn().mockReturnThis(),
				executeTakeFirst: jest.fn().mockResolvedValue(null),
			};

			(db.selectFrom as jest.Mock) = jest.fn().mockReturnValue(mockQuery);

			const result = await dao.hasHeatmapData("default", "2025-10-20");

			expect(result).toBe(false);
		});
	});
});
