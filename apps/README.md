# Apps Workspace

This directory contains the v1 implementation:

- `ui/`: Vite + React + TypeScript frontend with React Router.
- `server/`: FastAPI API and worker process.

## UI (local)

```bash
cd ui
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Server (local)

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run worker in another terminal:

```bash
cd server
uv run python worker.py
```

## Docker Compose (API + worker + postgres + ui)

```bash
cd /Users/mattsteffen/projects/llm/rincon-fire/apps
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- UI: `http://localhost:5173`
- Postgres: `localhost:5432`

## API routes

- `GET /api/v1/health`
- `GET /api/v1/models`
- `GET /api/v1/stations`
- `GET /api/v1/fire-areas/top?n=5&model_id=rf_baseline`
- `GET /api/v1/areas/{area_id}/weather/latest`
- `GET /api/v1/areas/{area_id}/predictions/latest?model_id=rf_baseline`
- `GET /api/v1/areas/{area_id}/satellite/latest`
- `GET /api/v1/location/weather/latest?lat=...&lon=...`
- `GET /api/v1/location/predictions/latest?lat=...&lon=...&model_id=rf_baseline`
- `GET /api/v1/location/satellite/latest?lat=...&lon=...`
- `GET /api/v1/satellite/files/{filename}`
