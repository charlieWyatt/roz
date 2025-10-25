# Roz Heatmap Viewer

Next.js app for viewing surveillance video heatmaps.

## Setup

```bash
# Install dependencies
npm install

# Add canvas dependency for server-side image generation
npm install canvas

# Add Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Run development server
npm run dev
```

Visit http://localhost:3000

## Features

- **Sidebar**: Lists all cameras from database
- **Calendar**: Select dates to view heatmaps
- **Heatmap Display**: Aggregates all minutes for selected date and renders as image

## API Routes

- `GET /api/cameras` - List all cameras
- `GET /api/heatmap?camera_id=X&date=YYYY-MM-DD` - Get heatmap metadata
- `GET /api/heatmap/image?camera_id=X&date=YYYY-MM-DD` - Get heatmap as JPEG

## Database

Connects to PostgreSQL using Kysely. Connection string in `.env.local`:

```
DATABASE_URL=postgresql://charlie:Sj28Qb50@localhost:5432/roz
```
