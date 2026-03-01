# Add the frontend to Railway (step-by-step)

Railway uses **Railpack** (Nixpacks is deprecated). The frontend service must have **Root Directory** set to `frontend` so Railpack detects Node/Next.js and uses `frontend/railpack.json`.

Your API is at **https://api-production-fdb3.up.railway.app**.  
Frontend URL (after setup): **https://frontend-production-d97f.up.railway.app**

---

## Option A: CLI (do as much as possible from terminal)

From repo root (with `railway link` already done for this project):

```bash
# 1. Create frontend service and set API URL (prompts: choose "Empty Service", name "frontend", add variable)
railway add --service frontend --variables "NEXT_PUBLIC_API_URL=https://api-production-fdb3.up.railway.app"

# 2. Generate public domain for frontend
railway domain -s frontend

# 3. Set Root Directory in dashboard (see below) — CLI cannot set this.

# 4. Deploy
./scripts/deploy_railway.sh frontend
```

**Dashboard (one-time):** Open the **frontend** service → **Settings** → **Source** → set **Root Directory** to **`frontend`**. If the service has no source, connect your GitHub repo first, then set Root Directory to `frontend`.

---

## Option B: Dashboard only

1. **Create service:** Project → **+ New** → **Empty Service** → name **`frontend`**.
2. **Source:** Settings → connect repo (if needed) → **Root Directory** = **`frontend`**.
3. **Variables:** Add `NEXT_PUBLIC_API_URL` = `https://api-production-fdb3.up.railway.app`.
4. **Domain:** Settings → **Networking** → **Generate domain**.
5. **Deploy:** From repo root run `./scripts/deploy_railway.sh frontend`.

---

## Deploy commands (from repo root)

```bash
# Deploy API
./scripts/deploy_railway.sh api

# Deploy frontend
./scripts/deploy_railway.sh frontend
```

To set or change frontend env vars via CLI:

```bash
railway variable set NEXT_PUBLIC_API_URL https://api-production-fdb3.up.railway.app -s frontend
```

---

## Quick reference

| Item | Value |
|------|--------|
| API URL | `https://api-production-fdb3.up.railway.app` |
| Frontend URL | `https://frontend-production-d97f.up.railway.app` |
| Frontend root directory | `frontend` (set in dashboard) |
| Required env var (frontend) | `NEXT_PUBLIC_API_URL=https://api-production-fdb3.up.railway.app` |
