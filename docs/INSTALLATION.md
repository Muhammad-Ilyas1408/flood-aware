# Installation Guide

This guide covers running Flood-Aware locally for development. For the live, deployed system, see [flood-aware.vercel.app](https://flood-aware.vercel.app) — no installation required.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python dependency management (this project does not use plain pip/requirements.txt) |
| Node.js | 18.18+ (20+ recommended) | Frontend runtime |
| npm | bundled with Node.js | Frontend package management |
| Git | any recent version | |

You will also need real API credentials for:
- **OpenAI** (`OPENAI_API_KEY`) — required, powers the decision agent and RAG embeddings/generation
- **OpenWeatherMap** (`OPENWEATHER_API_KEY`) — required, powers live weather data
- **Copernicus CDS / GloFAS** (`GLOFAS_API_KEY`) — optional; only required if you intend to run the offline forecast-ingestion script yourself. A recent forecast snapshot is already included in the repository for local development.

---

## 1. Clone the repository

```bash
git clone https://github.com/Muhammad-Ilyas1408/flood-aware.git
cd flood-aware
```

## 2. Backend setup

From the repository root:

```bash
uv sync
```

This installs all Python dependencies exactly as locked in `uv.lock`.

### Environment variables

Copy the example environment file and fill in your real credentials:

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

OPENAI_API_KEY=your-real-key
OPENWEATHER_API_KEY=your-real-key

### Run the backend

```bash
uv run uvicorn backend.app.main:app --reload --reload-dir backend
```

The API will be available at `http://localhost:8000`. Confirm it's running:

```bash
curl http://localhost:8000/health
```

**Note on first startup:** the backend eagerly parses regional GIS datasets on startup (typically well under a minute with the checked-in regional extracts). This is a deliberate, one-time cost per process start — subsequent requests are fast.

## 3. Frontend setup (Next.js — production)

```bash
cd frontend
npm install
```

Copy the example environment file:

```bash
cp .env.example .env.local
```

Confirm `NEXT_PUBLIC_API_BASE_URL` in `.env.local` points to your local backend:

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## 4. Dashboard setup (Streamlit — reference implementation)

From the repository root, with the backend dependencies already installed via `uv sync`:

```bash
streamlit run dashboard/Home.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`).

---

## Running Tests

```bash
uv run pytest --ignore=backend/tests/golden
```

To additionally run the real-API golden-set evaluation suite (requires a valid `OPENAI_API_KEY` and will make real, billed API calls):

```bash
$env:RUN_GOLDEN_SET="1"       # PowerShell
export RUN_GOLDEN_SET=1        # bash/zsh
uv run pytest backend/tests/golden/
```

---

## Common Issues

**`npm`/`node` not recognized after installation (Windows)** — close and fully restart your terminal (and any IDE with an integrated terminal), not just open a new tab. PATH updates from a fresh install are only picked up by newly launched processes.

**Backend fails at startup with a configuration error** — check that all required environment variables in `.env` are set; the application deliberately fails fast rather than starting in a broken state.

**GIS import errors on a fresh Linux environment** — `rasterio`/`fiona` (used for geospatial processing) may require system-level libraries (`libexpat1`, `libsqlite3-0`, `libcurl4`) not present on minimal container images. See `railpack.json` for the exact list used in production deployment.

---

## Production Deployment

The live system is deployed on Railway (backend) and Vercel (frontend). See `docs/CHANGELOG.md` (Sprint 16) for the full deployment process and configuration.

