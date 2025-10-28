# Roz Heatmap Visualization App

#### API Routes

- `/api/cameras` - List all available cameras
- `/api/heatmap/image?camera_id=X&date=YYYY-MM-DD` - Generate heatmap image

## Setup

### Prerequisites

- Node.js 18+
- PostgreSQL with heatmap data (populated by Python worker)

### Installation

```bash
npm install
```

### Environment Variables

Create `.env.local`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/roz
```

### Development

```bash
npm run dev
```

Open http://localhost:3000

### Testing

```bash
# Run all tests
npm test
```

### Deployments
Go to - Vercel and push buttons