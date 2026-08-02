# Flood-Aware Backend API Documentation

This document describes the real, current HTTP API exposed by the FastAPI
application defined in `backend/app/main.py` (`create_application()`). It was
written directly from the source in `backend/app/api/*.py` and
`backend/app/schemas/*.py` — every field name, type, constraint, and error
message below is read from the real code, not inferred.

## Base URL and conventions

- **API prefix:** none by default. `Settings.api_prefix` (`backend/app/config/settings.py`)
  defaults to `""`, so every route below is served unprefixed (e.g. `GET /health`,
  not `GET /api/v1/health`). If a deployment sets `FLOOD_AWARE_API_PREFIX`, prepend
  that value to every path in this document.
- **Content type:** all requests and responses use `application/json`.
- **Interactive docs:** the running application also serves Swagger UI at
  `/docs`, ReDoc at `/redoc`, and the raw OpenAPI schema at `/openapi.json`
  (see `create_application()` in `backend/app/main.py`).
- **CORS:** controlled by `FLOOD_AWARE_CORS_ALLOW_ORIGINS` (exact origin list)
  and `FLOOD_AWARE_CORS_ALLOW_ORIGIN_REGEX` (regex match), both read by
  `CORSMiddleware` in `create_application()`.
- **Response envelope:** most success responses share a common base
  (`backend/app/schemas/common.py`):
  - `BaseResponse` — just a `status` field (`"success"` or `"error"`, from
    `backend.app.models.enums.ResponseStatus`).
  - `SuccessResponse[DataT]` — adds `data: DataT` and an optional
    `metadata: BaseMetadata | None` (currently always `null` in real
    responses — no endpoint in this codebase populates it).
  - `VillageListResponse` and `ShelterListResponse` are `SuccessResponse[...]`
    specializations; `DatasetSummaryResponse` / `DatasetCatalogResponse` /
    `ConversationResponse` extend `BaseResponse` directly with their own
    explicit fields instead.

---

## `GET /health`

**Router:** `backend/app/api/health.py` · **Response model:** `HealthResponse`
(`backend/app/schemas/health.py`)

Returns the running service's health status and basic deployment metadata.
Reads live values from `Settings` (`backend/app/config/settings.py`) via
`get_settings()` — nothing here is hardcoded.

### Request

No parameters.

### Response — `200 OK`

| Field | Type | Notes |
|---|---|---|
| `timestamp` | `datetime` (timezone-aware, from `TimestampModel`) | Set to `datetime.now(UTC)` at request time. |
| `status` | `string`, min length 1 | Always the literal `"healthy"` (hardcoded in `get_health()`). |
| `application` | `string`, min length 1 | `Settings.application_name`, defaults to `"Flood-Aware"`. |
| `version` | `string`, min length 1 | `Settings.version`, defaults to `"0.1.0"`. |
| `environment` | `string`, min length 1 | `Settings.environment.value` — one of `"development"`, `"testing"`, `"production"` (`Environment` enum). |

`HealthResponse.model_config` uses `extra="ignore"` (the only schema in the
app that doesn't use `extra="forbid"`).

### Example response

```json
{
  "timestamp": "2026-08-03T09:15:42.118273+00:00",
  "status": "healthy",
  "application": "Flood-Aware",
  "version": "0.1.0",
  "environment": "production"
}
```

---

## `POST /conversation`

**Router:** `backend/app/api/conversation.py` · **Request model:**
`ConversationRequest` · **Response model:** `ConversationResponse`
(`backend/app/schemas/conversation.py`)

Executes or continues one grounded flood-decision conversation turn. Backed
by `ConversationOrchestrator.handle_turn()`
(`backend/app/conversation/orchestrator.py`):

- If `session_id` is omitted (`null`), a **new session is created** and its
  UUID is returned in the response.
- If `session_id` is provided and a matching session exists, the turn is
  appended to that session's history (the orchestrator reuses prior evidence
  when the new request doesn't change anything that would require
  re-collecting it — see `requires_new_evidence()`).
- If `session_id` is provided but does **not** match any existing session,
  the request fails with `404` (see [Error responses](#error-responses)).

### Request body — `ConversationRequest`

`model_config = ConfigDict(extra="forbid", frozen=True)` — unknown fields are
rejected (→ `422`).

| Field | Type | Required | Constraints |
|---|---|---|---|
| `session_id` | `UUID \| null` | No | Omit or `null` to start a new session. |
| `request_text` | `string` | **Yes** | `min_length=1`. |
| `coordinates` | `Coordinate \| null` | No | Object `{ "latitude": float, "longitude": float }`, `latitude` in `[-90, 90]`, `longitude` in `[-180, 180]` (`backend/app/graph/state.py`). |
| `village_name` | `string \| null` | No | Free text. |
| `district` | `string \| null` | No | Free text. |
| `province` | `string \| null` | No | Free text. |

### Response — `200 OK` — `ConversationResponse`

`model_config = ConfigDict(extra="forbid", frozen=True, strict=True)`. This is
deliberately the *minimal public surface* of the internal `Decision` model —
it excludes the full evidence bundle, conversation history, and the
grounding-only `reasons` / `supporting_evidence` fields that exist on the
internal `Decision` object but are not returned to API clients.

| Field | Type | Notes |
|---|---|---|
| `status` | `"success" \| "error"` | Defaults to `"success"`. |
| `session_id` | `UUID` | The session this turn belongs to (new or existing). |
| `risk_level` | enum string | One of `"normal"`, `"low"`, `"moderate"`, `"high"`, `"extreme"` (`backend.app.decision.models.RiskLevel` — **note:** this is a distinct enum from `backend.app.models.enums.RiskLevel`, which instead has `low/moderate/high/severe` and is not used by this endpoint). |
| `confidence` | enum string | One of `"low"`, `"medium"`, `"high"` (`DecisionConfidence`). |
| `summary` | `string`, min length 1 | Human-readable decision summary. |
| `actions` | array of `ActionResponse` | Each item: `{ "action": string (min_length=1), "priority": "low" \| "medium" \| "high" \| "critical" }` (`Priority` enum). Defaults to `[]`. |
| `citations` | array of `string` | Source citations backing the decision. Defaults to `[]`. |
| `missing_evidence` | array of `string` | Evidence gaps the decision flags as missing. Defaults to `[]`. |

### Example request

```json
{
  "session_id": null,
  "request_text": "Is it safe to stay in Bishbanr village tonight given the current river levels?",
  "coordinates": { "latitude": 34.75, "longitude": 72.35 },
  "village_name": "Bishbanr",
  "district": "Swat",
  "province": "Khyber Pakhtunkhwa"
}
```

### Example response

```json
{
  "status": "success",
  "session_id": "8f14e45f-ceea-4c4a-8b95-1e1f5b9a6a3d",
  "risk_level": "moderate",
  "confidence": "medium",
  "summary": "River discharge near Bishbanr is elevated but below the moderate-flood threshold; conditions warrant caution but not evacuation at this time.",
  "actions": [
    { "action": "Monitor GloFAS discharge updates every 6 hours.", "priority": "medium" },
    { "action": "Identify the route to Cadet College Swat shelter in case conditions worsen.", "priority": "low" }
  ],
  "citations": [
    "PDMA_KP_Inclusive_Summer_Hazards_Contingency_Plan.pdf"
  ],
  "missing_evidence": []
}
```

---

## `GET /villages`

**Router:** `backend/app/api/villages.py` · **Response model:**
`VillageListResponse` (`backend/app/schemas/datasets.py`)

Returns the complete configured village dataset (currently sourced from
`data/datasets/villages.csv`, 150 records).

### Request

No parameters.

### Response — `200 OK`

`VillageListResponse` is `SuccessResponse[tuple[VillageResponse, ...]]`:

| Field | Type | Notes |
|---|---|---|
| `status` | `"success" \| "error"` | Defaults to `"success"`. |
| `data` | array of `VillageResponse` | Full village list. |
| `metadata` | `null` | Always `null` — not populated by this endpoint. |

`VillageResponse` (`extra="forbid", frozen=True, strict=True`):

| Field | Type | Constraints |
|---|---|---|
| `name` | `string` | `min_length=1`. |
| `district` | `string` | `min_length=1`. |
| `population` | `integer \| null` | `ge=0` when present. |
| `latitude` | `float` | `-90 <= latitude <= 90`. |
| `longitude` | `float` | `-180 <= longitude <= 180`. |

**Note:** this API-facing `VillageResponse` schema only exposes 5 fields.
The real `data/datasets/villages.csv` file has many more real columns
(`village_id`, `tehsil`, `population_year`, `river_distance_km`,
`road_access`, `health_facility_nearby`, `school_nearby`,
`nearest_shelter_id`, `flood_risk`, `verification_status`, `data_source`) —
see `docs/DATA_INVENTORY.md` for the full CSV schema. Only `name`,
`district`, `population`, `latitude`, `longitude` are projected through to
this REST response; the rest are used internally (e.g. by the GIS/decision
pipeline) but not exposed here.

### Example response

```json
{
  "status": "success",
  "data": [
    {
      "name": "Bishbanr",
      "district": "Swat",
      "population": 7212,
      "latitude": 34.75,
      "longitude": 72.35
    }
  ],
  "metadata": null
}
```

---

## `GET /shelters`

**Router:** `backend/app/api/shelters.py` · **Response model:**
`ShelterListResponse` (`backend/app/schemas/datasets.py`)

Returns the complete configured shelter dataset (currently sourced from
`data/datasets/shelters.csv`, 51 records).

### Request

No parameters.

### Response — `200 OK`

`ShelterListResponse` is `SuccessResponse[tuple[ShelterResponse, ...]]`, same
envelope shape as `/villages` (`status`, `data`, `metadata: null`).

`ShelterResponse` (`extra="forbid", frozen=True, strict=True`):

| Field | Type | Constraints |
|---|---|---|
| `name` | `string` | `min_length=1`. |
| `district` | `string` | `min_length=1`. |
| `capacity` | `integer` | `ge=0`, **required** (unlike village `population`, this is not nullable). |
| `latitude` | `float` | `-90 <= latitude <= 90`. |
| `longitude` | `float` | `-180 <= longitude <= 180`. |

**Note:** as with villages, this is a narrow projection of the real CSV,
which also has `shelter_id`, `tehsil`, `building_type`,
`generator_available`, `water_available`, `medical_support`,
`female_facility`, `wheelchair_access`, `road_access`, `contact_number`,
`status`, `verification_status`, `last_updated`, `data_source` — see
`docs/DATA_INVENTORY.md`.

### Example response

```json
{
  "status": "success",
  "data": [
    {
      "name": "Cadet College Swat",
      "district": "Swat",
      "capacity": 500,
      "latitude": 34.82,
      "longitude": 72.46
    }
  ],
  "metadata": null
}
```

---

## `GET /datasets/catalog`

**Router:** `backend/app/api/datasets.py` · **Response model:**
`DatasetCatalogResponse` (`backend/app/schemas/datasets.py`)

Returns independent metadata + statistics summaries for the configured
village and shelter datasets (no record-level data — use `/villages` or
`/shelters` for that).

### Request

No parameters.

### Response — `200 OK` — `DatasetCatalogResponse`

`model_config = ConfigDict(extra="forbid", frozen=True, strict=True)`.

| Field | Type | Notes |
|---|---|---|
| `status` | `"success" \| "error"` | Defaults to `"success"`. |
| `villages` | `DatasetSummaryResponse` | See below. |
| `shelters` | `DatasetSummaryResponse` | Same shape, for the shelter dataset. |

`DatasetSummaryResponse` (extends `BaseResponse`):

| Field | Type | Notes |
|---|---|---|
| `status` | `"success" \| "error"` | Defaults to `"success"`. |
| `metadata` | `DatasetMetadata` | See below. |
| `statistics` | `DatasetStatistics` | `{ "record_count": integer >= 0 }`. |

`DatasetMetadata` (`backend/app/data/models.py`), as populated for the two
production catalog entries by
`create_production_dataset_catalog_config()` (`backend/app/config/datasets.py`):

| Field | Type | Real value for `villages` | Real value for `shelters` |
|---|---|---|---|
| `name` | `string` | `"Flood-Aware production villages"` | `"Flood-Aware production shelters"` |
| `description` | `string` | `"Verified village records for Flood-Aware decision support."` | `"Verified shelter records for Flood-Aware decision support."` |
| `version` | `string` | `"1.0.0"` | `"1.0.0"` |
| `source` | `string` | `"Flood-Aware checked-in dataset: villages.csv"` | `"Flood-Aware checked-in dataset: shelters.csv"` |
| `created_at` / `updated_at` | `datetime` (aware) | Derived from the CSV file's real filesystem timestamps at startup. | Same. |
| `coordinate_system` | `integer` (EPSG code) | `4326` (`CRS.WGS84`, an `IntEnum` — serializes as the plain integer, not a string). | `4326`. |
| `spatial_bounds` | `object \| null` | `null` (not set by the production config). | `null`. |
| `tags` | array of `string` | `["villages", "production"]` | `["shelters", "production"]` |

### Example response

```json
{
  "status": "success",
  "villages": {
    "status": "success",
    "metadata": {
      "name": "Flood-Aware production villages",
      "description": "Verified village records for Flood-Aware decision support.",
      "version": "1.0.0",
      "source": "Flood-Aware checked-in dataset: villages.csv",
      "created_at": "2026-07-23T11:02:11.609145+05:00",
      "updated_at": "2026-07-23T11:02:11.609145+05:00",
      "coordinate_system": 4326,
      "spatial_bounds": null,
      "tags": ["villages", "production"]
    },
    "statistics": { "record_count": 150 }
  },
  "shelters": {
    "status": "success",
    "metadata": {
      "name": "Flood-Aware production shelters",
      "description": "Verified shelter records for Flood-Aware decision support.",
      "version": "1.0.0",
      "source": "Flood-Aware checked-in dataset: shelters.csv",
      "created_at": "2026-07-23T11:04:19.811464+05:00",
      "updated_at": "2026-07-23T11:04:19.811464+05:00",
      "coordinate_system": 4326,
      "spatial_bounds": null,
      "tags": ["shelters", "production"]
    },
    "statistics": { "record_count": 51 }
  }
}
```

> `record_count` values (150 / 51) were counted directly from the real CSV
> files on disk at documentation time; `created_at`/`updated_at` timestamps
> shown are the real current file modification times, included as
> realistic examples — both will change if the CSV files are re-saved.

---

## Error responses

Every error response uses the same standardized shape, `ErrorResponse`
(`backend/app/schemas/errors.py`), produced by the exception handlers
registered in `create_application()` and implemented in
`backend/app/core/exceptions.py`:

```json
{
  "status": "error",
  "timestamp": "2026-08-03T09:15:42.118273+00:00",
  "status_code": 404,
  "detail": "string, 1-1000 chars",
  "path": "string, 1-2048 chars — the request path",
  "request_id": "string or omitted",
  "errors": [
    { "location": ["body", "field_name"], "message": "string", "error_type": "string" }
  ]
}
```

`errors` is only present for validation failures; other error types omit it
(the handler builds the payload with `exclude_none=True`).

### `404 Not Found` — conversation session not found

Raised by `handle_conversation_session_not_found_error()` when a
`ConversationSessionNotFoundError` propagates — i.e. a `POST /conversation`
request supplies a `session_id` that doesn't match any known session.

- **`status_code`:** `404`
- **`detail`** (exact, hardcoded text):
  `"The requested conversation session was not found. Start a new conversation."`

```json
{
  "status": "error",
  "timestamp": "2026-08-03T09:15:42.118273+00:00",
  "status_code": 404,
  "detail": "The requested conversation session was not found. Start a new conversation.",
  "path": "/conversation"
}
```

### `503 Service Unavailable` — decision generation failure

Raised by `handle_decision_generation_error()` when a
`DecisionGenerationError` propagates from `POST /conversation` (e.g. the
LangGraph run completes without producing a canonical `Decision`, or the
OpenAI-backed decision provider fails).

- **`status_code`:** `503`
- **`detail`** (exact, hardcoded text):
  `"The recommendation service is temporarily unavailable. Please try again."`

```json
{
  "status": "error",
  "timestamp": "2026-08-03T09:15:42.118273+00:00",
  "status_code": 503,
  "detail": "The recommendation service is temporarily unavailable. Please try again.",
  "path": "/conversation"
}
```

### `422 Unprocessable Content` — request validation error

Two distinct handlers produce this same status code:

**1. `handle_request_validation_error()`** — FastAPI/Pydantic request-parsing
failures (missing required field, wrong type, unknown field rejected by
`extra="forbid"`, coordinate out of range, etc.).

- **`status_code`:** `422` (`status.HTTP_422_UNPROCESSABLE_CONTENT`)
- **`detail`** (exact, hardcoded text): `"Request validation failed."`
- **`errors`:** one `ValidationIssue` per Pydantic error, each with
  `location` (the JSON path as a list, e.g. `["body", "request_text"]`),
  `message` (Pydantic's own error message), and `error_type` (Pydantic's
  error type string, e.g. `"string_too_short"`, `"missing"`).

```json
{
  "status": "error",
  "timestamp": "2026-08-03T09:15:42.118273+00:00",
  "status_code": 422,
  "detail": "Request validation failed.",
  "path": "/conversation",
  "errors": [
    {
      "location": ["body", "request_text"],
      "message": "String should have at least 1 character",
      "error_type": "string_too_short"
    }
  ]
}
```

**2. `handle_validation_exception()`** — internal domain `ValidationException`
subclasses (not raw Pydantic errors). Same `status_code` (`422`) and same
`detail` text (`"Request validation failed."`), but always exactly one
`ValidationIssue` whose `location` is `[exception.field]` (or `["validation"]`
if the exception has no specific field) and whose `error_type` is the
exception's Python class name.

### `500 Internal Server Error`

Two handlers both return an identical generic payload so internals are never
leaked to clients:

- **`handle_application_exception()`** — any `ApplicationError` subclass.
- **`handle_unexpected_exception()`** — any other unhandled `Exception`
  (also logged server-side via `logger.exception(...)`).

- **`status_code`:** `500`
- **`detail`** (exact, hardcoded text, identical for both):
  `"An unexpected server error occurred."`

### Generic HTTP exceptions

`handle_http_exception()` handles any raw Starlette `HTTPException` (e.g. a
`404` from an unmatched route). `detail` is the exception's own message if it
is a string, otherwise the fallback text `"Request failed."`. `status_code`
matches the exception's real status code.

---

## Endpoints not covered above

The application registers no other routes. The full route list, confirmed
from `backend/app/api/router.py`, is exactly the five endpoints documented
here: `GET /health`, `POST /conversation`, `GET /villages`, `GET /shelters`,
`GET /datasets/catalog`.
