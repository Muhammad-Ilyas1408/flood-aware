# Flood-Aware Data Inventory

This document inventories every real dataset the Flood-Aware backend
consumes (or has on disk), written directly from the actual files present
under `data/` and the code that reads them
(`backend/app/config/graph_dependencies.py`, `backend/app/forecast/constants.py`,
`backend/app/config/datasets.py`, `backend/app/rag/settings.py`). Sizes and
row counts below were measured directly from the files on disk at
documentation time.

---

## 1. Village dataset — `data/datasets/villages.csv`

- **Source:** manually curated/verified records; the real `data_source`
  column cites per-row provenance (e.g. `"GoharJageer.com (2017 Census)"`).
- **Format:** CSV, 150 data rows (plus header).
- **Real column schema** (header row read directly from the file):

  | Column | Sample value |
  |---|---|
  | `village_id` | `VC001` |
  | `village_name` | `Bishbanr` |
  | `district` | `Swat` |
  | `tehsil` | `Babuzai` |
  | `latitude` | `34.7500` |
  | `longitude` | `72.3500` |
  | `population` | `7212` |
  | `population_year` | `2017` |
  | `river_distance_km` | `2.0` |
  | `road_access` | `Yes` |
  | `health_facility_nearby` | `Partial` |
  | `school_nearby` | `Yes` |
  | `nearest_shelter_id` | `SHEL007` |
  | `flood_risk` | `Medium` |
  | `verification_status` | `Verified` |
  | `data_source` | `GoharJageer.com (2017 Census)` |

  Only 5 of these 16 columns (`village_name`→`name`, `district`,
  `population`, `latitude`, `longitude`) are projected through the REST API
  (`GET /villages` — see `docs/API_DOCUMENTATION.md`); the rest are read
  internally by the dataset repository/service layer but not exposed over
  HTTP today.
- **Approximate size:** a few tens of KB (150 rows, 16 columns of mostly
  short text/numeric fields).
- **Update/refresh process:** **no automated pipeline was found.** There is
  no script under `scripts/` that generates or refreshes this file — it is
  a manually maintained, hand-curated CSV edited directly. Flagging this
  explicitly rather than guessing a process exists.
- **Runtime wiring:** loaded via `create_production_dataset_catalog_config()`
  (`backend/app/config/datasets.py`), which points a `FileRepositoryConfig`
  at `data/datasets/villages.csv` and declares an explicit 5-column CSV
  schema (`name`, `district`, `population`, `latitude`, `longitude`,
  types `STRING`/`STRING`/`INTEGER`(nullable)/`FLOAT`/`FLOAT`) — this is the
  schema the *application* enforces, independent of the extra columns
  physically present in the CSV.

## 2. Shelter dataset — `data/datasets/shelters.csv`

- **Source:** manually curated/verified records; `data_source` cites
  per-row provenance (e.g. `"Wikipedia/Charbagh Tehsil"`).
- **Format:** CSV, 51 data rows (plus header).
- **Real column schema** (header row read directly from the file):

  | Column | Sample value |
  |---|---|
  | `shelter_id` | `SHEL001` |
  | `shelter_name` | `Cadet College Swat` |
  | `district` | `Swat` |
  | `tehsil` | `Charbagh` |
  | `latitude` | `34.8200` |
  | `longitude` | `72.4600` |
  | `capacity` | `500` |
  | `building_type` | `Educational Institution` |
  | `generator_available` | `Yes` |
  | `water_available` | `Yes` |
  | `medical_support` | `Partial` |
  | `female_facility` | `Yes` |
  | `wheelchair_access` | `Partial` |
  | `road_access` | `Yes` |
  | `contact_number` | `+92-946-XXXXXX` |
  | `status` | `Operational` |
  | `verification_status` | `Verified` |
  | `last_updated` | `2024-01-15` |
  | `data_source` | `Wikipedia/Charbagh Tehsil` |

  As with villages, only `shelter_name`→`name`, `district`, `capacity`,
  `latitude`, `longitude` are exposed via `GET /shelters`.
- **Approximate size:** a few tens of KB (51 rows, 19 columns).
- **Update/refresh process:** same as villages — **no automated pipeline
  found**; manually maintained CSV.
- **Runtime wiring:** same mechanism as villages, via
  `create_production_dataset_catalog_config()`, enforcing a 5-column
  application schema (`name`, `district`, `capacity` (non-nullable
  `INTEGER`), `latitude`, `longitude`).

## 3. Regional GIS extracts (OSM + WorldPop) — `data/gis/`

The running application only ever reads two specific files, hardcoded in
`backend/app/config/graph_dependencies.py`:

```python
_OSM_PBF_PATH = PROJECT_ROOT / "data/gis/osm/raw/swat-region.osm.pbf"
_WORLDPOP_RASTER_PATH = PROJECT_ROOT / "data/gis/worldpop/raw/swat-region_ppp_2025.tif"
```

Both are required at startup — `configure_graph_dependencies()` calls
`_require_existing_file()` on each before anything else runs; the app
refuses to start without them.

| File | Real size | Role |
|---|---|---|
| `data/gis/osm/raw/swat-region.osm.pbf` | ~4.3 MB | Regional OpenStreetMap extract (waterways, roads, bridges, amenity points/multipolygons) used by `RiverNetworkLoader` and `OSMLoader`, both eagerly warmed up (`.warm_up()`) once at application startup. |
| `data/gis/worldpop/raw/swat-region_ppp_2025.tif` | ~2.1 MB | Regional WorldPop 2025 population-density raster, used by `WorldPopLoader` / `PopulationExposureCalculator` for flood population-exposure estimates. |

- **Source / provenance:** both are derived, *not* original downloads —
  produced by `scripts/extract_regional_gis_data.py` from two much larger
  Pakistan-wide source files also present on disk:
  - `data/gis/osm/raw/pakistan-latest.osm.pbf` (~148 MB)
  - `data/gis/worldpop/raw/pak_ppp_2025.tif` (~135 MB)

  Per that script's own docstring, the extraction clips/buffers to
  `DEFAULT_SWAT_BOUNDING_BOX` (`backend/app/forecast/constants.py`:
  `min_latitude=34.70, min_longitude=72.15, max_latitude=35.00,
  max_longitude=72.55`) plus a ~0.2° margin, and is a **full spatial
  extract** (all nodes/ways/relations/tags preserved for OSM; a plain clip
  for the raster) — not a lossy tag filter — so every layer the loaders
  read survives unchanged. The script only ever creates new files; it never
  modifies the two Pakistan-wide originals.
- **Format:** `.osm.pbf` (OpenStreetMap Protocol Buffer binary), `.tif`
  (GeoTIFF raster).
- **Update/refresh process:** re-run `scripts/extract_regional_gis_data.py`
  whenever the upstream Pakistan-wide OSM/WorldPop sources are refreshed.
  It is a manually-run, standalone maintenance script — not part of the
  request path and not scheduled/automated.
- **Deployment note:** these two regional files are committed to git
  despite the repo's blanket `data/` gitignore rule (see the
  `.gitignore` exceptions added for Sprint 16.1 deployment prep), because
  Render/Railway's build only has what's in git and the app hard-fails at
  startup without them.

### Present on disk but **not currently used by the running application**

Two more GIS source files exist under `data/gis/` and are **not** referenced
anywhere in `backend/` (confirmed by search) — they appear to be raw
material for possible future work, not part of the current runtime path:

| File | Real size | Status |
|---|---|---|
| `data/gis/dem/raw/cop30_swat.tif` | ~132 MB | Copernicus 30m DEM, Swat-clipped. Not read by any current backend code. |
| `data/gis/admin/raw/pakistan_admin.zip` | ~13 MB | Pakistan administrative boundaries. Not read by any current backend code; also explicitly gitignored (`data/gis/admin/raw` was added as its own `.gitignore` rule). |

## 4. GloFAS forecast snapshots — `data/glofas/`

- **Source:** Copernicus Emergency Management Service GloFAS (Global Flood
  Awareness System) control forecast, via the EWDS/CDS API
  (`https://ewds.climate.copernicus.eu/api` by default —
  `ForecastSettings.glofas_base_url`, `backend/app/forecast/settings.py`).
- **Format:** NetCDF (`.nc`), one file per ingested snapshot, named
  `glofas_control_<UTC timestamp, ISO 8601 basic format>Z.nc` — e.g. the
  currently-committed
  `data/glofas/glofas_control_20260725T140327Z.nc` (~31 KB).
- **Location convention:** `DEFAULT_SNAPSHOT_DIRECTORY` in
  `backend/app/forecast/constants.py` resolves to `<project root>/data/glofas`.
  `SnapshotLocator` (`backend/app/forecast/snapshot_locator.py`) globs
  `glofas_*.nc` in that directory and selects the newest by
  `(file mtime, filename)` — **not** by parsing the filename's embedded
  timestamp itself, though in practice the two agree once ingestion and
  filesystem timestamps line up.
- **Staleness:** `DEFAULT_MAX_SNAPSHOT_AGE_HOURS = 48` — GloFAS publishes
  control forecasts once daily, so 48 hours tolerates one missed/delayed
  publish cycle before the app's existing staleness check flags the
  snapshot as stale. This is a real, currently-active check, not aspirational.
- **Update/refresh process:** `scripts/ingest_glofas_snapshot.py` — a
  manually-run script that authenticates against the EWDS/CDS API
  (`GLOFAS_API_KEY`), downloads one snapshot for the current UTC date via
  `GloFASClient`/`GloFASIngestionService`, and writes it into `data/glofas/`.
  The running API **never** triggers live ingestion itself — per the
  docstring in `backend/app/config/graph_dependencies.py`, it only ever
  reads whatever snapshot has already been ingested locally; ingestion is
  "a separate, independently-run process ... explicitly out of scope" for
  the request path.
- **Runtime behavior if missing/stale:** the app starts fine with no
  snapshot present (`SnapshotLocator` is only queried per-request, not at
  startup); a request needing a forecast will fail with
  `ForecastSnapshotNotFoundError` if no `.nc` file exists at all, or the
  forecast tool will surface the snapshot as stale if it's older than 48h.

## 5. Government knowledge base — `data/knowledge/` and `data/chroma/government/`

### Raw source documents — `data/knowledge/raw/`

Four PDF documents, listed directly (filenames + real sizes):

| File | Real size |
|---|---|
| `Disaster_Risk_Mapping_District_Swat.pdf` | ~3.6 MB |
| `National_Disaster_Management_Plan__NDMP__Main_Volume.pdf` | ~4.1 MB |
| `NDMA_National_Disaster_Risk_Reduction_Strategy_2025-2030.pdf` | ~1.4 MB |
| `PDMA_KP_Inclusive_Summer_Hazards_Contingency_Plan.pdf` | ~8.6 MB |

These are official Pakistani government/disaster-management source
documents (NDMA = National Disaster Management Authority; PDMA KP =
Provincial Disaster Management Authority, Khyber Pakhtunkhwa) used to ground
the RAG-based "government knowledge" tool with citable policy/guidance text.

### Indexed vector store — `data/chroma/government/`

- **Format:** a Chroma persistent collection (`chroma.sqlite3` +
  per-segment HNSW index directories — 21 files total, ~67 MB).
- **Collection name:** `government_disaster_knowledge`
  (`GovernmentKnowledgeSettings.collection_name`).
- **Embedding model:** `text-embedding-3-small` (OpenAI,
  `GovernmentKnowledgeSettings.embedding_model`).
- **Chunking:** semantic chunks up to 1,800 characters
  (`semantic_chunk_max_characters`).
- **Retrieval threshold:** `retrieval_score_threshold = 1.3` (squared-L2
  distance on unit-normalized embeddings; see the detailed comment in
  `backend/app/rag/settings.py` for the cosine-similarity derivation).
- **Update/refresh process:** `scripts/build_government_index.py` — an
  offline, deterministic rebuild: `GovernmentLoader` loads all PDFs from
  `data/knowledge/raw/`, `PDFCleaner` cleans extracted text,
  `SemanticChunker` splits it into ≤1,800-character chunks,
  `OpenAIEmbeddingService` embeds every chunk (requires `OPENAI_API_KEY`),
  then `ChromaVectorStore.clear()` + `.index()` **replaces** the entire
  `data/chroma/government/` collection from scratch. Re-run this script
  whenever the PDFs in `data/knowledge/raw/` change.
- **Deployment note:** like the GIS extracts, this directory is committed
  to git despite the blanket `data/` gitignore rule — without a populated
  vector store, the government-knowledge tool would return zero retrieval
  results on first deploy (an empty Chroma collection is not a startup
  failure, just an empty/degraded one).

### Evaluation benchmark — `data/knowledge/benchmarks/government_questions.json`

A small (~1.7 KB) benchmark question set, used by
`scripts/evaluate_government_knowledge.py` /
`scripts/sync_government_benchmark.py` to evaluate retrieval/response
quality offline. Not read by the running API.

---

## Summary table

| Dataset | Path | Format | Size | Rows/files | Refresh script |
|---|---|---|---|---|---|
| Villages | `data/datasets/villages.csv` | CSV | ~tens of KB | 150 rows | none (manual) |
| Shelters | `data/datasets/shelters.csv` | CSV | ~tens of KB | 51 rows | none (manual) |
| Regional OSM extract | `data/gis/osm/raw/swat-region.osm.pbf` | `.osm.pbf` | ~4.3 MB | 1 file | `scripts/extract_regional_gis_data.py` |
| Regional WorldPop extract | `data/gis/worldpop/raw/swat-region_ppp_2025.tif` | GeoTIFF | ~2.1 MB | 1 file | `scripts/extract_regional_gis_data.py` |
| Pakistan-wide OSM source | `data/gis/osm/raw/pakistan-latest.osm.pbf` | `.osm.pbf` | ~148 MB | 1 file | external download (not scripted in-repo) |
| Pakistan-wide WorldPop source | `data/gis/worldpop/raw/pak_ppp_2025.tif` | GeoTIFF | ~135 MB | 1 file | external download (not scripted in-repo) |
| DEM (unused by runtime) | `data/gis/dem/raw/cop30_swat.tif` | GeoTIFF | ~132 MB | 1 file | n/a |
| Admin boundaries (unused by runtime) | `data/gis/admin/raw/pakistan_admin.zip` | zip | ~13 MB | 1 file | n/a |
| GloFAS snapshot | `data/glofas/glofas_control_*.nc` | NetCDF | ~31 KB each | 1 committed | `scripts/ingest_glofas_snapshot.py` |
| Government knowledge PDFs | `data/knowledge/raw/*.pdf` | PDF | ~18 MB total | 4 files | n/a (source documents) |
| Government knowledge vector store | `data/chroma/government/` | Chroma/SQLite | ~67 MB | 21 files | `scripts/build_government_index.py` |
| Government knowledge benchmark | `data/knowledge/benchmarks/government_questions.json` | JSON | ~1.7 KB | 1 file | `scripts/sync_government_benchmark.py` (sync), `scripts/evaluate_government_knowledge.py` (eval) |

> **Note on external-download sources:** the two Pakistan-wide originals
> (OSM PBF, WorldPop raster) are large third-party downloads (OpenStreetMap
> planet extracts / WorldPop.org). No in-repo script re-downloads them —
> confirmed by inspecting `scripts/`; only their *derived, regional*
> extraction is scripted. Flagging this as read directly from the repo
> rather than assumed.
