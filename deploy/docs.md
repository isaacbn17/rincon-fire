```md
# Teaching Notes: `docker-compose.yml` (Backend + UI + Shared Data)

This document explains, line by line, what the provided `docker-compose.yml`
does, why it is structured this way, and how the two containers communicate.

---

## The Compose File (reference)

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    volumes:
      # Mount host ./data -> container /data
      - ./data:/data
    environment:
      # Common pattern: backend can allow CORS from the UI dev server if needed
      # - CORS_ORIGIN=http://ui:5173
      # Or if your backend expects the UI URL:
      # - UI_BASE_URL=http://ui:5173
      - PORT=8000
    expose:
      # Expose to other services on the compose network (not published to host)
      - "8000"
    ports:
      # Optional: publish backend to host for debugging/testing
      - "8000:8000"

  ui:
    build:
      context: ./ui
      dockerfile: Dockerfile
    depends_on:
      - backend
    environment:
      # Your Vite app should call the backend using this internal DNS name
      # e.g. fetch(`${import.meta.env.VITE_API_BASE_URL}/health`)
      - VITE_API_BASE_URL=http://backend:8000
    ports:
      # Assuming your UI container serves on 5173 (Vite) or 80 (nginx).
      # Keep 5173 here if you're running the Vite dev server inside Docker.
      - "5173:5173"
```

---

## 1. What Docker Compose is doing here (high-level)

Docker Compose orchestrates multiple containers as a single “application.”

In this setup, we have:

- **`backend`**: a Python HTTP server built from `./backend/Dockerfile`
- **`ui`**: a React + Vite + npm UI built from `./ui/Dockerfile`
- A **shared host directory** `./data` mounted into the backend container at
  `/data`
- A **private network** created automatically by Compose so the containers can
  talk to each other by name (`backend`, `ui`)

Key idea: Compose makes multi-container development predictable:
same commands (`docker compose up`), same networking, repeatable builds.

---

## 2. Top-level structure: `services`

```yaml
services:
  backend:
    ...
  ui:
    ...
```

A **service** in Compose is a definition of how to run a container (or set of
identical containers). Each service typically maps to one “component” in a
system.

Why separate services?

- Separation of concerns (UI vs API)
- Independent builds and runtime configuration
- Easier scaling or replacement later (e.g., swap the UI serving method)

---

## 3. Building images from local Dockerfiles: `build`

### Backend build

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile
```

**What it means:**

- `context: ./backend` tells Docker: “When building, treat `./backend` as the
  build context.” The build context is the folder whose contents can be copied
  into the image with `COPY` instructions.
- `dockerfile: Dockerfile` means: use `./backend/Dockerfile`.

**Why it’s done this way:**

- You want the backend image to be built from the code in the backend directory.
- It keeps the Compose file aligned with a common repo structure:

```
repo/
  docker-compose.yml
  backend/
    Dockerfile
    ...
  ui/
    Dockerfile
    ...
  data/
```

### UI build

```yaml
ui:
  build:
    context: ./ui
    dockerfile: Dockerfile
```

Same concept: build the UI image from the UI directory.

**Teaching point:**
You could also use `image: some-registry/some-tag` to pull a prebuilt image, but
for students learning, building locally is clearer and ensures they’re running
their code.

---

## 4. Mounting host data into a container: `volumes`

```yaml
backend:
  volumes:
    - ./data:/data
```

This is a **bind mount** (host folder mapped into container).

- Left side: `./data` (a directory on the host, relative to the Compose file)
- Right side: `/data` (a directory path inside the container)

**Why mount data?**

- Persistence: containers are ephemeral. If the backend writes to its internal
  filesystem, that data disappears when the container is removed.
- Development convenience: you can inspect/edit data on the host and the
  container sees it immediately.

**Important behavior:**
- If `./data` doesn’t exist, Docker will typically create it on the host (exact
  behavior can vary by OS/permissions). For teaching, it’s best to explicitly
  create it: `mkdir -p data`.

**Common student pitfalls:**
- Permissions issues (especially on Linux). If the container runs as a different
  UID/GID than the host user, it might not be able to write to `/data`.
- Path confusion: `./data` is relative to the location of `docker-compose.yml`,
  not relative to where the command is run (Compose resolves it relative to the
  project directory).

---

## 5. Environment variables: `environment`

### Backend environment

```yaml
backend:
  environment:
    - PORT=8000
```

This sets an environment variable inside the container. Many Python servers
(Flask, FastAPI/uvicorn wrappers, custom scripts) use a `PORT` variable to choose
which port to bind to.

**Why include it?**

- It makes the container configurable without modifying code.
- Students learn the “12-factor app” style: configuration in environment.

**Note:** Your backend must actually read `PORT` for this to matter. If it always
binds to 8000 in code, this env var is redundant (but still a good teaching
pattern).

### UI environment

```yaml
ui:
  environment:
    - VITE_API_BASE_URL=http://backend:8000
```

This is a typical pattern for Vite apps: configure an API base URL via an env
var.

**Why `http://backend:8000` and not `http://localhost:8000`?**

Inside the UI container, **`localhost` means the UI container itself**, not the
host machine and not the backend container.

Compose creates a private DNS entry for each service name, so:

- `backend` resolves to the backend container’s IP on the Compose network
- Therefore `http://backend:8000` reaches the backend from the UI container

This is a foundational Docker networking concept and one of the main lessons in
this example.

**Important Vite nuance:**
Vite only exposes environment variables prefixed with `VITE_` to the browser
bundle. That’s why it’s `VITE_API_BASE_URL`.

---

## 6. Service-to-service networking in Compose (the “talk to each other” part)

Compose automatically creates:

- A **network** for the project (unless you define your own)
- DNS-based service discovery

So by default:

- `backend` can reach `ui` at `http://ui:<port>`
- `ui` can reach `backend` at `http://backend:<port>`

No extra network configuration is needed for basic cases.

### `expose` vs `ports`

#### `expose`

```yaml
backend:
  expose:
    - "8000"
```

`expose` means: “This port is intended to be reachable by other containers on
the same Docker network.”

- It does **not** publish the port to the host.
- It’s mainly documentation plus some metadata.

**Key teaching point:**
Even without `expose`, containers on the same network can often still connect if
the service is listening on that port; `expose` is not strictly required in many
cases. But it’s useful for clarity.

#### `ports`

```yaml
backend:
  ports:
    - "8000:8000"
```

This publishes the backend port to the host:

- Left side (`8000`) is the host port
- Right side (`8000`) is the container port

So from your laptop, you can hit `http://localhost:8000`.

**Why include it?**
- Great for debugging, demos, and students testing the API directly with a
  browser or curl.

**But it’s optional** for container-to-container communication. The UI does not
need host port publishing to reach the backend.

### UI ports

```yaml
ui:
  ports:
    - "5173:5173"
```

This publishes the UI to the host at `http://localhost:5173`.

Why 5173?
- That’s Vite’s default dev server port.

**Teaching point: dev-server vs production**
- If your UI Dockerfile runs `npm run dev -- --host 0.0.0.0 --port 5173`,
  publishing 5173 makes sense.
- If instead your UI Dockerfile builds static assets and serves them via nginx,
  the container likely listens on port 80; in that case you’d use:

```yaml
ports:
  - "5173:80"
```

(or more commonly `- "3000:80"` / `- "8080:80"`—the host port is arbitrary).

---

## 7. Startup ordering: `depends_on`

```yaml
ui:
  depends_on:
    - backend
```

This tells Compose: start the backend container before starting the UI container.

**Important teaching nuance:**
- `depends_on` controls start order, but it does **not** guarantee the backend is
  “ready to accept connections.”
- For readiness, you typically add:
  - a healthcheck on `backend`, and
  - logic in UI or a reverse proxy that retries.

But for many student projects, `depends_on` is enough to avoid obvious race
conditions at startup.

---

## 8. How the browser fits into this (common confusion)

There are *two* network perspectives:

1. **Container-to-container** (inside Docker):
   - UI container reaches backend container at `http://backend:8000`

2. **User’s browser-to-backend** (outside Docker, on your host network):
   - Browser reaches backend at `http://localhost:8000` (because of `ports`)

If your React app runs in the browser and tries to fetch `http://backend:8000`,
that will **not work** from the browser, because `backend` is only resolvable
inside Docker.

So which is correct?

- If the UI server (e.g., Vite dev server) is proxying API requests from browser
  to backend, then internal addressing can work.
- If the browser directly calls the API, you’ll use `http://localhost:8000`
  (or a reverse proxy domain) in the browser environment.

This is one of the most valuable conceptual lessons in Docker networking.

---

## 9. Why we did *not* define custom networks here

Compose defaults are intentionally simple:

- A single isolated network per Compose project
- Automatic DNS names equal to service names

For teaching:
- Fewer moving parts
- Introduces the “service name DNS” concept early

Later extensions can include:
- multiple networks (e.g., public/private)
- network aliases
- reverse proxy service (nginx/Traefik)

---

## 10. Practical run commands (for students)

From the repo root:

```bash
mkdir -p data
docker compose up --build
```

Stopping:

```bash
docker compose down
```

Reset everything including anonymous volumes (not used here, but good to know):

```bash
docker compose down -v
```

---

## 11. Common improvements (optional teaching add-ons)

### A) Healthcheck (readiness)
Add a healthcheck to backend and only start UI after backend is healthy (Compose
v2 has limited conditional support, but healthchecks are still valuable):

- Add a `/health` endpoint in backend
- Add healthcheck in compose

### B) Dev-time source code mounts
For rapid iteration, mount backend source and/or UI source into containers, but
that requires your Dockerfiles and entrypoints to support reload (e.g. uvicorn
`--reload`, Vite dev server with proper host binding).

### C) CORS
If UI is served from `localhost:5173` and backend from `localhost:8000`,
the browser enforces CORS. Backend must allow the UI origin.

That’s why the compose file includes commented examples like `CORS_ORIGIN`.

---

## Summary (what students should remember)

- `build` builds images from local folders/Dockerfiles.
- `volumes` bind mounts host directories into containers for persistence and
  inspection.
- Compose gives you **automatic networking + DNS**: service names become
  hostnames (`backend`, `ui`).
- `ports` publishes container ports to the host; `expose` is internal/documentary.
- `depends_on` controls startup ordering, not full readiness.

---
```