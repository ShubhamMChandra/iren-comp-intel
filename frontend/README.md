# Iren Sales Intelligence — Frontend

Next.js frontend for the Iren Sales Intelligence Platform. Connects to the FastAPI backend at `http://localhost:8000`.

## Pages

- `/` — Dashboard: top prospects, recent signals, score trends
- `/prospects` — Filterable prospect list with scores, drill-downs, AI briefs
- `/compete` — Competitor cards and side-by-side comparisons
- `/admin` — Company management and system settings

## Development

```bash
npm install
npm run dev
```

Requires the API server running on port 8000. See the [root README](../README.md) for setup.
