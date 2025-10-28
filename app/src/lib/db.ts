import { Kysely, PostgresDialect } from "kysely";
import { Pool } from "pg";

interface HeatmapMinutesTable {
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

interface Database {
	heatmap_minutes: HeatmapMinutesTable;
}

const pool = new Pool({
	connectionString: process.env.DATABASE_URL,
	max: 10,
	// Supabase requires SSL in all environments
	ssl: {
		rejectUnauthorized: false, // Required for Supabase pooler
	},
});

export const db = new Kysely<Database>({
	dialect: new PostgresDialect({
		pool,
	}),
});
