# AgentTracer Platform - React UI

Modern React + TypeScript UI for the AgentTracer Platform.

## Features

- 📊 **Dashboard** - Real-time statistics and insights
- 🔍 **Run Explorer** - Search and filter agent runs
- 📈 **Trace Timeline** - Visual step-by-step execution timeline
- ⚠️ **Failure Analysis** - Semantic failure breakdown with recommendations

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend APIs running (Ingest API on :8000, Query API on :8001)

### Installation

```bash
# Navigate to UI directory
cd ui

# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will open at http://localhost:3000

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
ui/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── RunExplorer.tsx       # Run list with filters
│   │   ├── TraceTimeline.tsx     # Step timeline visualization
│   │   └── FailureBreakdown.tsx  # Failure analysis
│   ├── pages/            # Page components
│   │   ├── Dashboard.tsx         # Stats and overview
│   │   └── RunDetail.tsx         # Single run detail view
│   ├── App.tsx           # Main app with routing
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── index.html            # HTML template
├── package.json          # Dependencies
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── postcss.config.js     # PostCSS configuration
```

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Configuration

### API Endpoints

The UI connects to:
- **Ingest API**: http://localhost:8000
- **Query API**: http://localhost:8001

To change these, update the `QUERY_API_URL` constant in each component.

### Port

The development server runs on port 3000 by default. Change in `vite.config.ts`:

```typescript
server: {
  port: 3000,
  open: true,
}
```

## Components

### Dashboard
- Real-time statistics
- Success rate tracking
- Failure type breakdown
- Step distribution
- Recent activity feed

### Run Explorer
- Paginated run list
- Advanced filters (agent_id, version, status, environment, time range)
- Click-through to detailed view
- Status indicators

### Run Detail
- Complete run metadata
- Visual step timeline
- Latency visualization
- Retry attempt highlighting
- Failure analysis with recommendations

### Trace Timeline
- Ordered step sequence
- Step type color coding
- Latency bars
- Expandable metadata
- Retry detection
- Summary statistics

### Failure Breakdown
- Semantic failure classification
- Step linkage
- Actionable recommendations
- Failure type distribution

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Routing
- **TanStack Query** - Data fetching
- **Axios** - HTTP client
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Recharts** - Charts (optional)

## Development

### Adding a New Page

1. Create component in `src/pages/`
2. Add route in `src/App.tsx`
3. Update navigation

### Adding a New Component

1. Create component in `src/components/`
2. Export from component file
3. Import where needed

### Type Safety

All components use TypeScript with strict mode enabled. Define interfaces for props and API responses.

## Deployment

### Static Hosting

Build and deploy to any static hosting:

```bash
npm run build
# Upload dist/ to hosting provider
```

### Docker

See main project `Dockerfile` and `docker-compose.yml` for containerized deployment.

### Nginx

Serve the built files with Nginx:

```nginx
server {
    listen 80;
    server_name observability.yourdomain.com;

    root /var/www/agent-obs-ui;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Privacy & Security

This UI follows Phase-1 privacy constraints:
- ✅ Displays safe metadata only
- ❌ Never displays prompts or responses
- ❌ Never displays PII
- ❌ Never displays chain-of-thought

All sensitive data filtering happens at the API layer.

## Troubleshooting

### API Connection Errors

Ensure backend services are running:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Build Errors

Clear node_modules and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Errors

Check TypeScript configuration:

```bash
npx tsc --noEmit
```

## Performance

- Lazy loading for route-based code splitting
- React Query caching (5-minute stale time)
- Pagination for large data sets
- Optimized re-renders with proper React patterns

## Accessibility

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Screen reader friendly

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Contributing

1. Follow existing code style
2. Add TypeScript types
3. Test in development mode
4. Build successfully before submitting

## License

Same as parent project.
