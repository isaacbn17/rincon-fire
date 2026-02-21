# Server

FastAPI API + background worker for Rincon Fire v1.

## Local

1. Create/install dependencies (example with uv):

```bash
uv sync
```

2. Run API:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Run worker (separate terminal):

```bash
uv run python worker.py
```
