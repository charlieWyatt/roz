import { inflate } from "zlib";
import { promisify } from "util";
import sharp from "sharp";
import { AggregatedHeatmapData } from "@/lib/dao/heatmapDao";

const inflateAsync = promisify(inflate);

/**
 * Colormap for heatmap visualization (Jet colormap)
 * Maps normalized intensity (0-1) to RGB color
 */
function applyJetColormap(normalized: number): [number, number, number] {
	// Clamp to 0-1 range
	const value = Math.max(0, Math.min(1, normalized));

	let r, g, b;

	if (value < 0.125) {
		r = 0;
		g = 0;
		b = 0.5 + value * 4;
	} else if (value < 0.375) {
		r = 0;
		g = (value - 0.125) * 4;
		b = 1;
	} else if (value < 0.625) {
		r = (value - 0.375) * 4;
		g = 1;
		b = 1 - (value - 0.375) * 4;
	} else if (value < 0.875) {
		r = 1;
		g = 1 - (value - 0.625) * 4;
		b = 0;
	} else {
		r = 1 - (value - 0.875) * 4;
		g = 0;
		b = 0;
	}

	return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

/**
 * Decompress a single heatmap intensity array from the database.
 */
async function decompressHeatmap(
	compressedData: Buffer,
	height: number,
	width: number
): Promise<Float32Array> {
	// Decompress the zlib-compressed data
	const decompressed = await inflateAsync(compressedData);

	// Convert to Float32Array
	const float32Array = new Float32Array(
		decompressed.buffer,
		decompressed.byteOffset,
		decompressed.byteLength / Float32Array.BYTES_PER_ELEMENT
	);

	// Validate dimensions
	if (float32Array.length !== height * width) {
		throw new Error(
			`Invalid heatmap dimensions: expected ${height * width}, got ${float32Array.length}`
		);
	}

	return float32Array;
}

/**
 * Aggregate multiple heatmap arrays by summing them.
 */
async function aggregateHeatmaps(
	data: AggregatedHeatmapData
): Promise<Float32Array> {
	const { height, width, records } = data;
	const size = height * width;
	const aggregated = new Float32Array(size);

	// Sum all heatmaps
	for (const record of records) {
		const heatmap = await decompressHeatmap(
			record.intensity_array,
			height,
			width
		);
		for (let i = 0; i < size; i++) {
			aggregated[i] += heatmap[i];
		}
	}

	return aggregated;
}

/**
 * Generate a heatmap image as a JPEG buffer.
 */
export async function generateHeatmapImage(
	data: AggregatedHeatmapData,
	options: {
		colormap?: "jet" | "hot";
		quality?: number;
	} = {}
): Promise<Buffer> {
	const { colormap = "jet", quality = 90 } = options;
	const { height, width } = data;

	// Aggregate all heatmaps
	const aggregated = await aggregateHeatmaps(data);

	// Find max value for normalization
	let maxValue = 0;
	for (let i = 0; i < aggregated.length; i++) {
		if (aggregated[i] > maxValue) {
			maxValue = aggregated[i];
		}
	}

	// Avoid division by zero
	if (maxValue === 0) {
		maxValue = 1;
	}

	// Create RGB image buffer
	const imageBuffer = Buffer.alloc(width * height * 3);

	for (let i = 0; i < aggregated.length; i++) {
		const normalized = aggregated[i] / maxValue;
		const [r, g, b] = applyJetColormap(normalized);

		const pixelIndex = i * 3;
		imageBuffer[pixelIndex] = r;
		imageBuffer[pixelIndex + 1] = g;
		imageBuffer[pixelIndex + 2] = b;
	}

	// Use sharp to create JPEG
	const image = await sharp(imageBuffer, {
		raw: {
			width,
			height,
			channels: 3,
		},
	})
		.jpeg({ quality })
		.toBuffer();

	return image;
}

/**
 * Generate a heatmap image with statistics overlay (optional future enhancement)
 */
export interface HeatmapStats {
	totalMinutes: number;
	totalIntensity: number;
	maxIntensity: number;
	avgIntensity: number;
}

export function calculateHeatmapStats(
	data: AggregatedHeatmapData
): HeatmapStats {
	const totalIntensity = data.records.reduce(
		(sum, r) => sum + r.total_intensity,
		0
	);
	const maxIntensity = Math.max(...data.records.map((r) => r.max_intensity));

	return {
		totalMinutes: data.totalMinutes,
		totalIntensity,
		maxIntensity,
		avgIntensity: totalIntensity / data.totalMinutes,
	};
}
