import { describe, it, expect, beforeEach, jest } from "@jest/globals";
import { NextRequest } from "next/server";

// Mock the database connection
jest.mock("@/lib/db", () => ({
	db: {
		selectFrom: jest.fn(),
	},
}));

// Mock the dependencies BEFORE importing the route
const mockGetAggregatedHeatmapData = jest.fn();
const mockGenerateHeatmapImage = jest.fn();

jest.mock("@/lib/dao/heatmapDao", () => ({
	HeatmapDao: jest.fn().mockImplementation(() => ({
		getAggregatedHeatmapData: mockGetAggregatedHeatmapData,
	})),
}));

jest.mock("@/lib/services/heatmapImageGenerator", () => ({
	generateHeatmapImage: mockGenerateHeatmapImage,
}));

// Now import the route after mocks are set up
import { GET } from "../route";

describe("/api/heatmap/image", () => {
	beforeEach(() => {
		jest.clearAllMocks();
		mockGetAggregatedHeatmapData.mockReset();
		mockGenerateHeatmapImage.mockReset();
	});

	it("should return 400 if camera_id is missing", async () => {
		const request = new NextRequest(
			"http://localhost:3000/api/heatmap/image?date=2025-10-20"
		);

		const response = await GET(request);
		const data = await response.json();

		expect(response.status).toBe(400);
		expect(data.error).toBe("camera_id and date required");
	});

	it("should return 400 if date is missing", async () => {
		const request = new NextRequest(
			"http://localhost:3000/api/heatmap/image?camera_id=default"
		);

		const response = await GET(request);
		const data = await response.json();

		expect(response.status).toBe(400);
		expect(data.error).toBe("camera_id and date required");
	});

	it("should return 404 if no heatmap data exists", async () => {
		mockGetAggregatedHeatmapData.mockResolvedValue(null);

		const request = new NextRequest(
			"http://localhost:3000/api/heatmap/image?camera_id=default&date=2025-10-20"
		);

		const response = await GET(request);
		const data = await response.json();

		expect(response.status).toBe(404);
		expect(data.error).toBe("No data found for this date");
		expect(mockGetAggregatedHeatmapData).toHaveBeenCalledWith(
			"default",
			"2025-10-20"
		);
	});

	it("should return image buffer when data exists", async () => {
		const mockHeatmapData = {
			height: 180,
			width: 320,
			records: [
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
			],
			totalMinutes: 1,
		};

		const mockImageBuffer = Buffer.from("fake-image-data");

		mockGetAggregatedHeatmapData.mockResolvedValue(mockHeatmapData);
		mockGenerateHeatmapImage.mockResolvedValue(mockImageBuffer);

		const request = new NextRequest(
			"http://localhost:3000/api/heatmap/image?camera_id=default&date=2025-10-20"
		);

		const response = await GET(request);

		expect(response.status).toBe(200);
		expect(response.headers.get("Content-Type")).toBe("image/jpeg");
		expect(response.headers.get("Cache-Control")).toBe("public, max-age=3600");

		const buffer = await response.arrayBuffer();
		expect(Buffer.from(buffer)).toEqual(mockImageBuffer);

		expect(mockGenerateHeatmapImage).toHaveBeenCalledWith(mockHeatmapData, {
			quality: 90,
		});
	});

	it("should return 500 if image generation fails", async () => {
		const mockHeatmapData = {
			height: 180,
			width: 320,
			records: [],
			totalMinutes: 0,
		};

		mockGetAggregatedHeatmapData.mockResolvedValue(mockHeatmapData);
		mockGenerateHeatmapImage.mockRejectedValue(
			new Error("Image generation failed")
		);

		const request = new NextRequest(
			"http://localhost:3000/api/heatmap/image?camera_id=default&date=2025-10-20"
		);

		const response = await GET(request);
		const data = await response.json();

		expect(response.status).toBe(500);
		expect(data.error).toBe("Failed to generate image");
		expect(data.details).toBe("Image generation failed");
	});
});
