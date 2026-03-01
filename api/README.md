# API (FastAPI)

Backend for Iren Sales Intelligence. Deployed on Railway.

## Railway setup (one-time)

1. **Volume** (persistent SQLite): In Railway dashboard → **api** service → **Volumes** → **Add Volume** → mount path `/data`, size 1 GB. Without this, the DB is ephemeral.

2. Env vars are set via CLI; optionally add `OPENROUTER_API_KEY` in the dashboard for AI features.

## Deploy

From repo root:

```bash
railway link          # if not already linked
railway service api   # use api service
railway up
```

Or from this directory:

```bash
railway up
```

API URL: **https://api-production-fdb3.up.railway.app** (or your generated domain from `railway domain`).

## Full stack (API + frontend) on Railway

Same project, two services:

| Service   | Root directory | Deploy from   |
|-----------|----------------|---------------|
| **api**   | repo root      | `railway service api && railway up` (from repo root) |
| **frontend** | `frontend`  | In dashboard: add service → deploy from repo, set **Root Directory** to `frontend`. Set env `NEXT_PUBLIC_API_URL` to the api service URL (e.g. `https://api-production-xxx.up.railway.app`). Then `railway service frontend && railway up` from repo root, or deploy from UI. |
