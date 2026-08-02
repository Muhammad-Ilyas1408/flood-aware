# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

---

## [1.6.0] - 2026-08-02

---

# Sprint 16 – Production Deployment (2026-08-02)

Full production deployment of both services: FastAPI backend to Railway, Next.js frontend to Vercel. Both free-tier, no Docker (native platform builders). Deployed from the frontend-nextjs branch; not yet merged into dev/main (deliberate — verify live deployment fully before merging).

---

## Sprint 16.1 — Backend Deployment (Railway)

### Investigated

- Full pre-deployment audit: app factory/entrypoint (`backend.app.main:app`), dependency management (uv, no requirements.txt needed), every environment variable the app reads across all pydantic-settings classes, host/port binding requirements, and — critically — which local data files are actually required at runtime versus safely excludable.
- Confirmed GloFAS snapshot and Chroma vector store loading are lazy (not eagerly validated at startup, unlike the GIS regional extracts), meaning missing them would degrade functionality gracefully rather than crash — informed the decision below.

### Fixed

- **Platform selection: Render → Railway.** Render's current free-tier terms require a payment card on file, with real, current (2026) user reports of unexpected charges on the free tier despite no card being technically "required" in Render's own marketing language. Verified via direct research (Render's own pricing page confirming "$0/mo + compute" — i.e., compute is billed separately from the free workspace tier) before committing to a platform. Pivoted to Railway, confirmed via research to offer genuine no-card-required deployment (a $5 trial credit, sufficient for a lightweight service).
- **Committed required runtime data to git**, overriding the blanket `data/` gitignore rule via explicit negated patterns (verified correct in an isolated scratch repository first, given git's known "cannot re-include a file whose parent directory is excluded" gotcha): the two regional GIS extracts (~6.4MB, from the prior session's Sprint 14.4 work), the populated Chroma government-knowledge vector store (~67MB — without this, Policy Advisor would be completely non-functional on first deploy), and the single most recent GloFAS snapshot (~32KB, correctly identified by its filename-encoded reference timestamp rather than an unreliable on-disk copy mtime).
- **Real deployment blocker found and fixed: missing system libraries for GDAL-wrapping wheels.** First deploy attempt crashed with `ImportError: libexpat.so.1: cannot open shared object file` at `import rasterio` — Railway's base container image doesn't ship `libexpat`, a system library `rasterio`'s (and `fiona`'s) manylinux wheels expect the host to provide rather than bundle, per the manylinux packaging policy. Root-caused via direct research against authoritative sources (Railpack's own config docs, `rasterio`'s and `fiona`'s real GitHub issue trackers documenting the identical failure in other minimal-image environments, and the manylinux external-library allowlist) rather than guessed. Added `railpack.json` specifying `libexpat1`, plus `libsqlite3-0` and `libcurl4` proactively (same class of issue, commonly needed alongside `libexpat1` for the GDAL/PROJ stack, included preemptively to avoid a second failed-deploy cycle).

### Verified

- Live health check (`GET /health`) returns `200 healthy` from real Railway infrastructure.
- **Real GIS warm-up on production hardware completed in ~2 seconds** (river network: 517ms, OSM infrastructure: 800ms) — direct, concrete confirmation that the prior session's regional-extraction work (Hotfix 14.4) wasn't just a local optimization; it's what made this deployment's cold-start time viable at all.
- Real end-to-end `POST /conversation` call against live Railway infrastructure returned a correctly grounded, correctly non-fabricating response (moderate risk, real GIS/weather citations, honest `missing_evidence` for absent shelter/village data) — full pipeline confirmed working on real deployed infrastructure, not just locally.

---

## Sprint 16.2 — Frontend Deployment (Vercel)

### Fixed

- **Vercel's initial-import screen has no branch selector** — defaults to the repository's default branch (`main`), which does not contain `frontend/` (only `frontend-nextjs` does). Resolved by completing the initial import against `main` (an expected, harmless failed/404 first deployment, since the project must exist before its settings can be changed), then correcting the **Production environment's branch tracking** (found under Settings → Environments → Production in the current Vercel UI — not a simple "Production Branch" dropdown under Git settings, as in prior UI versions) to `frontend-nextjs`, and the **Root Directory** (Settings → Build and Deployment) to `frontend`.
- **A stale "Output Directory: public" setting** (an artifact of the initial, framework-undetected first deployment attempt against `main`) caused subsequent Production builds to fail with `Error: No Output Directory named "public" found`, despite the underlying Next.js build itself succeeding correctly (confirmed via the build log's own route manifest, showing all four real routes compiled). Cleared to let Vercel's Next.js framework preset handle output location automatically, as intended.
- Used a **Deploy Hook** (a project-specific webhook URL that triggers a build of a named branch) to force fresh, correctly-configured builds while iterating on the above settings, since Vercel's standard auto-deploy-on-push didn't apply here (no new commits were being pushed during this configuration phase).

### Verified

- Live production deployment at `https://flood-aware.vercel.app`, confirmed all four routes (Home, Agent, Policy Advisor, Situation Room) render correctly with real data from the live Railway backend.

---

## Sprint 16.3 — Cross-Origin (CORS) Production Hardening

### Fixed

- **Real CORS failure in production, distinct from the original Sprint 15.3 CORS fix.** Vercel generates a unique, permanent, randomly-suffixed URL for every individual deployment (in addition to the stable production domain and a branch-specific domain) — the original exact-string `cors_allow_origins` list, sufficient for local development, cannot account for URLs that don't exist yet at configuration time and change on every future deploy.
- Added `cors_allow_origin_regex` (a new, separate setting alongside the existing exact-match list, both active simultaneously via Starlette's `CORSMiddleware`, which supports both mechanisms together) — **explicitly rejected the first, looser draft pattern** (`https://flood-aware.*\.vercel\.app`) after identifying it would incorrectly trust *any* Vercel project merely starting with "flood-aware," regardless of owner, since Vercel project-name slugs aren't globally exclusive beyond simple registration. Final pattern additionally pins the match to the actual, globally-unique Vercel account slug, closing that gap.
- Verified the exact origin-matching behavior of the installed Starlette version's `CORSMiddleware` directly against its real source (`.fullmatch`, not a looser substring/prefix check) before finalizing the pattern, and tested the final regex against both all three real observed production URLs (all correctly matched) and five adversarial cases — a different project with the same prefix, a different account with a similar suffix, a domain-spoofing subdomain trick (`flood-aware.vercel.app.evil.com`), and a wrong-scheme (`http://`) origin — all correctly rejected.

### Verified

- Live, real cross-origin request from `https://flood-aware.vercel.app` to `https://flood-aware-production.up.railway.app/conversation` succeeds correctly; a real Policy Advisor question returned a genuine, grounded, NDMP-cited answer.
- Full production walkthrough confirmed working end-to-end: Flood-Aware Agent (grounded conversation, honest absent-evidence handling), Policy Advisor (real RAG citations), Situation Room (real dataset stats, real map).

### Notes

- Both services remain on free/no-cost tiers as intended — Railway's trial credit model and Vercel's Hobby tier, neither requiring payment information.
- `frontend-nextjs` is not yet merged into `dev`/`main`, and the Streamlit dashboard (`dashboard/`) has not yet been retired — both deliberately deferred to a dedicated follow-up session now that live deployment is fully confirmed working, rather than rushed immediately after this session's real, substantial debugging work.
- Real, live, publicly reachable URLs: frontend `https://flood-aware.vercel.app`, backend `https://flood-aware-production.up.railway.app`.
- Sprint 16 (backend deployment, frontend deployment, CORS production-hardening) is functionally complete and fully verified live.

---

## [1.5.0] - 2026-08-01

---

# Sprint 15 – Next.js Production Frontend (2026-08-01)

New, separate frontend on its own branch (frontend-nextjs), built entirely against the existing, unmodified FastAPI backend. The Streamlit dashboard (dashboard/) remains fully intact and working throughout as a reference implementation — not deployed, not deleted, retained until this frontend fully supersedes it.

---

## Sprint 15.1 — Project Scaffolding & Design System

### Added

- Scaffolded `frontend/`: Next.js 16 (App Router), TypeScript, Tailwind CSS v4, ESLint, `src/` structure, shadcn/ui (Radix-based components).
- Real design system in `src/app/globals.css`: navy/amber color scale derived directly from the existing Streamlit dashboard's brand anchors (background #0B1220, secondary background #151F32, border #2A3A55, accent #F59E0B), full 11-step Tailwind color scales, plus dedicated semantic risk-level tokens (`risk-normal`/`moderate`/`high`/`extreme`) consumed via soft-tint badges, never hardcoded per component.
- Font pairing via `next/font`: Inter (body) + Space Grotesk (headings), replacing Next's default font stack.
- Foundational reusable primitives: `Card`, `Badge` (extended with risk-level variants), `PageShell` (consistent page layout wrapper).
- Typed API contracts (`src/types/`) mirroring the real backend's Pydantic schemas exactly (`ConversationRequest`/`Response`, `VillageResponse`, `ShelterResponse`, `DatasetCatalogResponse`), and a typed API client (`src/lib/api-client.ts`).

### Fixed

- Node.js was not installed on the development machine; installed via `winget` and diagnosed/resolved a PATH-propagation issue (required a full VS Code restart, not just a new terminal, since VS Code's integrated terminals inherit PATH from when VS Code itself launched).
- A CSS comment containing a literal `*/` sequence inside a code example prematurely terminated the comment block, breaking the build — found via a real dev-server run (not just a syntax check) and fixed.

### Verified

- `npm run lint` / `npx tsc --noEmit` clean. Real dev server run confirmed the design tokens, fonts, and Card/Badge primitives render correctly, including direct inspection of the compiled CSS output.

---

## Sprint 15.2 — Home Page

### Added

- Real production Home page (`src/app/page.tsx`): hero section with live stats (villages monitored, shelters tracked) fetched server-side at request time via an async Server Component — not a client-side loading flash — with a graceful, silent soft-fail if the backend is unreachable (standard practice for a landing page, not an error banner).
- Three feature cards (Flood-Aware Agent, Policy Advisor, Situation Room) with distinct icons, accurate descriptions, and real hover/keyboard-focus states.

### Verified

- Live stats confirmed pulling real numbers (150 villages, 51 shelters) directly from `GET /datasets/catalog`, not mocked. Confirmed responsive down to mobile width via DevTools device simulation.

---

## Sprint 15.3 — Flood-Aware Agent (Chat)

### Added

- Real multi-turn chat interface (`src/app/agent/`): village selector (real data from `GET /villages`, real coordinates auto-populated, no manual lat/lon entry, "Other / not listed" fallback), message history in local component state, rotating honest status messages while awaiting a response, risk/confidence badges, priority-labeled actions, collapsible citations.
- Distinct, user-facing handling for all three real failure modes (404 session-not-found with auto-fresh-session, 503 service-unavailable with no silent auto-retry, network failure), matching the Streamlit version's already-correct behavior.
- Deliberate DOM structure (three flex siblings: header, scrollable message list, input) designed from the start to guarantee bottom-pinned input positioning — informed directly by the multiple rounds of layout bugs this exact problem caused in the Streamlit version.

### Fixed

- **CORS preflight failure (real backend change).** The backend had no CORS middleware configured, since it had never previously been called from an actual browser (Streamlit makes server-side Python requests, which aren't subject to browser CORS enforcement). `POST /conversation`'s preflight `OPTIONS` request was rejected with 405, blocking every conversation call from the new frontend. Added `CORSMiddleware` to `backend/app/main.py`, registered outermost (after existing middleware, so CORS headers apply even to error responses), with environment-driven allowed origins (`cors_allow_origins` in `Settings`, defaulting to local dev origins, overridable per environment for future deployment). Verified via a direct in-process `TestClient` simulation of the exact failing preflight (now 200 with correct headers), confirmed plain requests with no Origin header (how every existing backend test calls the app) are completely unaffected, and confirmed a disallowed origin correctly receives no CORS headers (the fix is properly scoped, not wide open).

### Verified

- Full real, unmocked live test: real village selection, real question, real grounded 200 response (risk/confidence/summary/actions/citations all correctly rendered), real follow-up reusing the same `session_id` with confirmed evidence-reuse speedup (~24s → ~4s, consistent with prior backend-level findings), and confirmed the shelter-absent-evidence honesty behavior (no fabricated capacity/names) holds correctly in the new frontend too.
- Backend full test suite unaffected by the CORS change (275 passed, 2 skipped — consistent with all prior sessions).

---

## Sprint 15.4 — Policy Advisor

### Added

- Second, lighter-weight chat page (`src/app/policy-advisor/`), sharing all chat mechanics with Flood-Aware Agent via an extracted `useConversation` hook (refactored out of Agent's page, confirmed behaviorally identical via a real regression test after extraction). No village selector — location fields always omitted, relying on existing backend routing (absent coordinates correctly skip GIS/Weather/Forecast) to route purely through Knowledge/Dataset.
- `showRiskBadges` prop added to the shared message-rendering component (default `true`), set to `false` on Policy Advisor — risk/confidence badges are conceptually wrong for pure policy questions, matching the same fix already made in the Streamlit version.
- Policy-appropriate rotating status messages and page copy.

### Verified

- Real, unmocked policy question returned a real grounded answer citing real NDMP source pages, with badges correctly absent. Agent page confirmed unaffected by the shared-hook extraction via an identical real regression request.

---

## Sprint 15.5 — Situation Room

### Added

- Real district overview page (`src/app/situation-room/`): dataset provenance cards (real record counts, version, source), sortable/filterable village and shelter tables, and — a genuine improvement over the Streamlit version — a real interactive map (`react-leaflet`) with real per-record markers for every village and shelter, using the actual coordinates now available since Sprint 14's backend fix (the Streamlit version predates that fix and could only ever show a dataset-level bounding box).
- `react-leaflet@5` chosen specifically for React 19 compatibility (confirmed via real peer-dependency inspection against the installed React version — the older `react-leaflet@4.x` targets React 18 only and would have been silently incompatible).

### Verified

- Real SSR output confirmed exact live record counts (150/51) and real village/shelter names in the tables. Real marker coordinates confirmed flowing from the live API. Sort/filter logic verified against real fetched data (population/capacity sorting, district filtering). Live visual confirmation: map renders correctly with real amber (village) and green (shelter) markers, clickable with real detail popups.

---

## Sprint 15.6 — Global Navigation & Visual Polish

### Added

- Persistent site header (`src/components/site-header.tsx`), rendered once in the root layout so it appears on all four pages automatically — real client-side navigation via Next.js `<Link>`, active-page indication via `usePathname()` matched against real routes and marked with the real `aria-current="page"` accessibility attribute (not just a visual class), smooth animated underline transition, and a mobile hamburger menu (shadcn `Sheet`) for narrow viewports. Resolves a real, significant usability gap: prior to this, there was no way to navigate between pages without returning to Home first.
- Home hero: centered layout (previously left-aligned) with a deliberate staggered entrance animation (headline → value proposition → stats, ~150ms offsets).
- Chat pages: extracted, restyled "Start new conversation" as a shared, properly weighted button component with a brand-consistent amber hover treatment; added a matching page-title icon to Flood-Aware Agent (previously missing, inconsistent with Policy Advisor/Situation Room).
- Chat message entrance animation (fade + slide-in, keyed correctly so only newly-appended messages animate, not the full history on every render — verified via React's keyed-list reconciliation behavior, not assumed), a fast staggered reveal for each response's parts (badges → summary → actions → citations), and a smooth cross-fade for the rotating status messages (replacing an instant text swap).

### Fixed

- **Cramped chat message area — root-caused through three iterative rounds, each confirmed with progressively deeper verification:**
  1. The chat pages' own `PageShell` never zeroed its default `py-8`/`sm:py-10` padding, which — combined with `box-sizing: border-box` — was being effectively double-subtracted against the hand-written `calc()` height formula, silently shrinking the available content area by 128–160px. Compounded by the site header's own padding not being fully neutralized at the `sm:` breakpoint, making its real rendered height taller than the formula assumed. Fixed by zeroing padding on both elements and correcting the formula to subtract only the real header height.
  2. A residual 1px clipping issue remained: the header's own `border-bottom` (1px) sits outside `box-sizing: border-box`'s scope for an `auto`-height element (border/padding only get automatically absorbed for elements with an *explicit* height, not auto-sized ones) — an exact, 100%-reproducible discrepancy at every breakpoint. Fixed by including the real 1px border in the calc() formula, plus added an `env(safe-area-inset-bottom)`-aware buffer to the input form for notched/gesture-nav devices (resolves to 0 on ordinary screens, free insurance elsewhere).
  3. Even after both mathematically-exact fixes, real-world testing still showed a few clipped pixels at the input's bottom border — pure `calc()` precision proved insufficient against real browser rendering variance (subpixel rounding, engine-specific `100dvh` behavior). Diagnosed via direct DevTools Computed-style inspection (not further formula reasoning) confirming the element itself was correctly sized with zero problematic padding, pointing to the outer container's lack of a hard overflow boundary. Added `overflow-hidden` to the outer container (verified not to interfere with the independently-scrolling inner message list, and confirmed the village selector's portal-rendered dropdown is unaffected), plus a final pragmatic ~10px safety buffer — deliberately trading a small amount of theoretical precision for real-world robustness, which fully resolved the issue.

### Verified

- All fixes confirmed via inspection of the actual rendered DOM class list after `twMerge` resolution (not just compiled-CSS class presence, which was identified as the specific verification gap that let the original bug through undetected across two earlier "verified correct" rounds) and, for the final round, direct browser DevTools Computed-style ground truth.
- `npm run lint` / `npx tsc --noEmit` clean throughout every round. Real, live, human visual confirmation on both `/agent` and `/policy-advisor` that the message area now fills the available space correctly with no clipping, on both desktop and mobile widths.

### Notes

- This session's most valuable debugging lesson: two consecutive rounds of CSS fixes were each individually, provably correct (verified against real compiled/rendered output) yet did not resolve the visible symptom — the correct response was not a third theoretical fix, but stepping back to gather real DevTools ground-truth evidence, which immediately revealed the actual remaining cause. Worth carrying forward as a general debugging principle for this project.
- The Streamlit dashboard (`dashboard/`) remains fully intact, untouched, and functional throughout Sprint 15 — retained as the working reference implementation until this Next.js frontend is deployed and can fully replace it.
- No backend changes in this sprint beyond the CORS middleware addition (Sprint 15.3), which is additive and confirmed to not affect any existing backend test or behavior.
- Ready for final pre-deployment review, or further page-specific feature work, per priority.

---

## [1.4.0] - 2026-07-31

---

# Sprint 14 – Production Backend, Streamlit Dashboard & Visual Identity (2026-07-29 to 2026-07-31)

---

## Sprint 14.1 – Production Composition Root & Conversation API (2026-07-29)

### Sprint 14.1.1 — Production Graph Composition Root

#### Added

- Added `backend/app/config/graph_dependencies.py`: `configure_graph_dependencies()`, constructing the full real tool stack (village/shelter/dataset services and tools, GIS river/OSM/WorldPop loaders + `GISDomainService`, government knowledge tool, real `build_openai_decision_provider()`) exactly once at FastAPI application startup, mirroring `scripts/manual_chat.py`'s composition but as a true singleton stored on `application.state` rather than rebuilt per invocation.
- Added `get_conversation_orchestrator(request)`, a request-scoped dependency provider matching the existing `get_village_service(request)` pattern.
- Added `close_graph_dependencies()`, releasing vector store/river/WorldPop loader resources at application shutdown.
- Wired both into `main.py`'s existing lifespan sequence, idempotently guarded.
- Weather and Forecast use deterministic static stand-ins as a deliberate v1.0 scope decision (real integration in 14.1.4 below).

#### Verified

- Fails fast with a clear `ApplicationConfigurationError` if required GIS data files or `OPENAI_API_KEY` are missing at startup, rather than accepting traffic and failing on first request.

---

### Sprint 14.1.2 — POST /conversation Endpoint

#### Added

- Added `backend/app/schemas/conversation.py`: `ConversationRequest`/`ConversationResponse`, exposing only client-appropriate fields (risk level, confidence, summary, actions, citations, missing_evidence) — internal fields (full evidence bundle, reasons, conversation history) explicitly excluded from the response surface, verified by dedicated test assertions.
- Added `backend/app/api/conversation.py`: `POST /conversation`, registered in the existing router aggregation, following the established villages/shelters router conventions exactly.
- Added `backend/tests/test_conversation_api.py`: integration tests using `app.dependency_overrides`, no real OpenAI/GIS calls.

#### Fixed

- **Request-schema strict-mode defect:** `ConversationRequest` originally inherited `strict=True`, which rejects `session_id: UUID` unless the caller supplies an already-constructed Python `UUID` object — impossible for any real JSON client, since JSON has no native UUID type. This made the documented "supply a session_id to continue a conversation" contract unsatisfiable for every real caller. Removed `strict=True` from the inbound request schema (response schemas remain strict). Audited all other request fields; confirmed none share this defect.
- **Unhandled `DecisionGenerationError` mapped to 503:** added `handle_decision_generation_error`, returning a clean, generic "temporarily unavailable" message with safe server-side logging (exception type only, never message/internals), registered ahead of the catch-all handler.
- **Unhandled unknown-session `ValueError` mapped to 404:** added `backend/app/conversation/exceptions.py` (`ConversationError`/`ConversationSessionNotFoundError`, following the existing `decision/exceptions.py` domain-hierarchy convention) and `handle_conversation_session_not_found_error`, returning a safe "session not found, start a new conversation" message. Test explicitly asserts neither the raw session UUID nor the exception class name appear in the response body.

#### Verified

- Full test suite: 260 passed, 1 skipped.
- Live end-to-end verification against a real running server: real multi-turn conversation with real GIS/village/shelter/knowledge tools and real OpenAI reasoning; observed the Sprint 13 retry-with-feedback mechanism recover live from a real grounding correction; confirmed evidence reuse (no GIS re-parse) on same-context follow-up; confirmed real 404 for an unknown session ID and real 503 handling.

---

### Sprint 14.1.3 — Multi-Turn Reasoning Focus (initial pass)

#### Added

- Added a FOCUS instruction to `PromptBuilder._SYSTEM_INSTRUCTIONS`' conversation-history paragraph, with a weak/strong contrast example built from real captured production output: follow-up questions must primarily address what the current request specifically asks, using prior turns for continuity only.
- Added `test_follow_up_narrows_focus_to_shelters_not_general_overview`, a real multi-turn golden-set scenario.

#### Notes — measurement methodology finding

- Initial test design measured focus via a shelter-action ratio threshold; proved unreliable not because the prompt fix was ineffective, but because the underlying metric (a ratio over 2–3 discrete actions) cannot support a stable threshold comparison — real API variance moved the ratio between 0.33/0.5/0.67 across identical calls. Replaced with a coarser, structural pass/fail check: at least one action must be shelter-grounded, and the first action specifically must be shelter-grounded. Verified stable across 3 consecutive real-API runs plus the full 17-test golden set.

---

### Sprint 14.1.4 — Real Weather & Forecast Integration

#### Added

- Wired real `WeatherTool` (OpenWeatherMap, synchronous per-request) into the production composition root, replacing `_StaticWeatherTool`. Fails fast at startup via `ApplicationConfigurationError` if `OPENWEATHER_API_KEY` is missing.
- Wired real `GloFASForecastTool` into the production composition root, replacing `_StaticForecastProvider`. Reads only the newest already-ingested local snapshot from `data/glofas/`; deliberately never triggers live GloFAS/CDS ingestion from the request path (the underlying `cdsapi` client has an unbounded blocking poll loop unsuitable for a synchronous request handler). Ingestion remains a separate, independently-run process (`scripts/ingest_glofas_snapshot.py`).
- Added snapshot staleness detection: `ForecastEvidence` gained `snapshot_age_hours`/`snapshot_stale` fields, computed from the snapshot file's modification time against a configurable threshold (`GLOFAS_MAX_SNAPSHOT_AGE_HOURS`, default 48h — one full tolerated missed/delayed GloFAS daily publication cycle).
- Staleness is surfaced **both internally and to the end user**, via the existing `missing_evidence` mechanism: a stale forecast produces a human-readable notice (e.g. "forecast (data is approximately 4 days old)") and causes confidence reasoning to treat it as non-authoritative.
- Removed both static stand-in classes entirely — no dead code left behind.

#### Fixed

- **`ForecastNode` never populated `evidence.forecast`:** the node only ever wrote to `state.forecast_result`, leaving `state.forecast` (the field the prompt actually reads) permanently at its empty default. This meant every prior conversation session reported "forecast" as entirely absent even when real discharge data existed. Fixed as part of enabling staleness representation; existing test assertion updated to reflect corrected, intentional behavior.

#### Verified

- Full test suite: 267 passed, 1 skipped. Full golden set: 17/17 passing.
- Live end-to-end verification across two real villages (Mingora — major severity, full tool suite; Barikot — normal severity, minimal tool suite): real weather/forecast values genuinely differ per location; staleness notice correctly surfaced; system correctly declined to fabricate shelter guidance when genuinely absent; correctly produced a shelter-led follow-up when genuinely present.

#### Notes

- Real finding, deferred: since tool routing is purely severity-based (Sprint 12), a user's explicit question cannot itself trigger GIS/Village/Shelter collection if computed severity alone wouldn't have — the same query-intent-routing gap Sprint 12 already identified, now with a concrete example. Recommended as scoped future work.
- GloFAS ingestion scheduling (periodic automated refresh) remains a separate, deferred follow-up task.

---

### Sprint 14.1.5 — GIS Loader Eager-Parse Caching

#### Added

- Added `warm_up()` to `RiverNetworkLoader` and `OSMLoader`, eagerly parsing the full-extent Pakistan-wide OSM PBF dataset once, ahead of any request. Both loaders now retain the parsed layer(s) in memory and serve every subsequent request via spatial clipping instead of re-reading from disk.
- `configure_graph_dependencies()` calls `warm_up()` on both loaders at startup. `OSMLoader` gained a `close()` method for symmetric shutdown cleanup.

#### Fixed

- **Root cause identified and resolved:** GDAL's OSM vector driver has no persistent spatial index for `.osm.pbf` files — a `bbox=` filter narrows returned *results*, not the underlying *scan cost*, which is dominated by total file size. Every fresh-evidence turn re-parsed the entire dataset from scratch (measured: 28–92s river network, 65–220s OSM infrastructure). Real per-request GIS collection time reduced from ~90 seconds–4 minutes to ~30 seconds by moving the expensive parse to a one-time startup cost.

#### Verified

- Two new tests per loader, including a self-enforcing `side_effect` pattern that raises `StopIteration` on any unintended second disk read.
- Live verification: a real fresh-evidence turn against a warmed-up server completed in 30.4 seconds (previously 2–4 minutes), GIS evidence confirmed intact and correct.

#### Notes

- Tradeoff accepted deliberately: startup time grows by the one-time full parse cost, paid once rather than repeated per request — matches the project's real usage pattern (server started once, serves many requests).
- Regional PBF extraction (pre-clipping the source file) identified as the most durable long-term fix, explicitly deferred as a future data-preparation task.
- **Sprint 14.1 fully complete.**

---

## Sprint 14.2 – Streamlit Dashboard & Production Hardening (2026-07-30)

### Sprint 14.2.1 — Situation Analysis Page

#### Added

- Added `dashboard/` Streamlit application (`app.py`, `config.py`, `api_client.py`), a thin client calling only existing, tested FastAPI endpoints — no business logic duplicated in the frontend.
- Added `dashboard/pages/situation_analysis.py`: dataset catalog summary, filterable village/shelter tables, and a dataset-level bounding-box map with an explicit, honest notice when per-record coordinates are unavailable rather than fabricating positions.
- Added `streamlit`, `streamlit-folium`, `folium` as real dependencies (versions confirmed against PyPI, not assumed).

---

### Sprint 14.2.2 — AI Assistant Chat Page

#### Added

- Added `dashboard/pages/ai_assistant_chat.py`: real multi-turn chat UI wired to `POST /conversation`, using `st.chat_message`/`st.chat_input`, session-state-persisted history, colored risk/confidence badges, prioritized action lists, and a collapsible citations panel.
- Added rotating, honestly-worded progress messages during the real multi-second/minute wait (background thread performs the blocking API call; only the main thread touches Streamlit UI elements) — a deliberate choice over fabricating fake granular progress, since true per-node streaming isn't available from the backend.
- Added distinct, user-facing handling for all three real failure modes: session-not-found (404, auto-starts a new conversation), recommendation-service-unavailable (503, no silent auto-retry), and generic connection failure — verified live against real triggered failures.

#### Fixed

- **Manual coordinate entry removed entirely.** `GET /villages`/`GET /shelters` previously discarded real latitude/longitude columns that already existed in the source CSVs, at a hardcoded 3-column projection layer. This silently forced every chat request through either a village with no real location data or manual lat/lon entry. Extended the schema/DTO/API chain (`DatasetColumnType`, `VillageDTO`/`ShelterDTO`, `VillageResponse`/`ShelterResponse`) to surface real coordinates end-to-end; the chat page now auto-derives coordinates from the selected village with zero manual entry.

---

### Sprint 14.2.3 — Real-Traffic Production Fixes

Found and fixed via live dashboard testing — not surfaced by any automated test suite, since mocked fixtures didn't reproduce these real-data conditions.

#### Fixed

- **RAG retrieval had no relevance floor.** `ChromaVectorStore.search()`'s existing `score_threshold` parameter was never actually passed by either of its two callers, so retrieval always returned Chroma's raw top-5 nearest neighbors unconditionally — including weak/boilerplate matches (a repeated PDF title/preamble page was cited as "government policy" guidance in live testing). Wired a real, empirically-derived threshold (confirmed Chroma's squared-L2 distance metric and OpenAI embedding normalization before deriving the number) through `KnowledgeTool`/`GovernmentRetriever`/`ChromaVectorStore`; zero-results-above-threshold now returns an honest "no sufficiently relevant guidance found" result without calling the LLM. Extended `ContextBuilder` deduplication to catch near-duplicate boilerplate text across different chunk IDs.
- **Root-caused FOCUS instability.** `ConversationOrchestrator`/`RecommendationNode` never passed the current turn's raw request text into `decide()` — only the evidence bundle and prior-turn history. The FOCUS prompt instruction was asking the model to "address what the CURRENT request specifically asks about" while the current request's text was never actually present anywhere in the prompt — a structural data-flow gap, not a prompt-wording problem, explaining the instability across multiple same-day wording attempts. Added a `current_request_text` parameter (backward-compatible) threaded through `decide()`/`PromptBuilder.build()`/both real call sites; live re-verification confirmed a real "what about shelters" follow-up now correctly leads with named, specific shelter details.

#### Verified

- Full suite: 274 passed, 2 skipped. Full golden set: 18/18 passing.
- Extensive live, real-API, real-UI verification across multiple villages and multi-turn conversations, including a real observed 503 with correct handling and successful recovery on resend.

---

### Sprint 14.2.4 — Shelter-Action Grounding Refinement

#### Fixed

- **Entirely-absent evidence categories could still generate specific, actionable-sounding recommendations.** A response could honestly state "no shelter data available" in `missing_evidence` while simultaneously recommending a specific action ("assess and prepare existing shelters, ensuring they are stocked") — not a hallucinated citation, but an inconsistent, over-specific claim about a category with zero real evidence behind it.
- Added `DecisionActionGroundingError` (a `DecisionGroundingError` subclass) and `DecisionParser._validate_no_actions_on_absent_categories()`, enforced at the parser level, consistent with this project's established pattern (prompt instruction + parser-level enforcement).
- **Refined through three rounds of empirical verification, each correcting a real gap found by the previous round's own test:**
  1. Initial check (reference-subset only) correctly caught the real bug, but the retry-correction message carried no structured feedback, so the model couldn't reliably self-correct — fixed by adding `rejected_action`/`absent_category` fields and a dedicated correction-message builder, with careful attention to Python's multiple-inheritance `except` clause ordering.
  2. Reference-subset alone proved too strict: it rejected the prompt's own "strong" example behavior — a legitimate general action ("obtain shelter data before finalizing evacuation planning") that cited only shelter-related dataset provenance. Citation shape cannot distinguish *acquiring* missing information from making a *specific claim* about an absent resource.
  3. Final fix: the check now requires **both** reference-subset-of-absent-category **and** action text matching a specific-claim pattern (stock/prepare/assess/activate/ready/capacity) before rejecting — general data-gathering language is always allowed. Verified empirically against all four relevant real examples before considering the fix complete.

#### Verified

- Full suite: 275 passed, 2 skipped. Full golden set: 19/19 passing, including 3 consecutive stable runs of the refined test.
- One unrelated golden test (`test_shelter_recommendation`, Sprint 11's single-turn golden set) failed once on exact citation-string phrasing, then passed twice on immediate re-run — logged as observed, non-reproducing variance.

#### Notes

- This fix is a strong example of iterative refinement done correctly: each round was driven by a real test failure exposing a genuine design gap, not speculative tuning.
- No changes to `route_after_gis`/graph routing (confirmed correct and untouched throughout this investigation).
- **Sprint 14.2 fully complete.**

---

## Sprint 14.3 – Visual Identity & Policy Advisor (2026-07-31)

### Added

- Real visual theme (`.streamlit/config.toml`): deep navy/slate background with a warm amber accent, deliberately distinct from Streamlit's default dark theme. Risk/confidence badge colors (`st.badge`) left on Streamlit's defaults after confirming they remain high-contrast against the new background — avoided silently changing badge semantics while restyling around them.
- Added a shared `dashboard/components/header.py` (`render_header()`), giving every page consistent branding, plus a sidebar brand caption anchored via Streamlit's own `aria-current="page"` accessibility hook (not a fragile text/order-based hack) for active-page highlighting, colored via `st.get_option` to stay in sync with the theme automatically.
- Added `dashboard/pages/Policy_Advisor.py`: a second, lighter-weight chat page for government policy/disaster-management guidance questions. Sends no village/coordinates (always `None`), relying on existing backend routing (absent coordinates correctly skip GIS/Weather/Forecast, per Sprint 12) to route purely through Knowledge/Dataset — no unnecessary GIS wait for policy-only questions.
- Renamed pages for real product naming (via `git mv`, preserving history): "AI Assistant Chat" → **Flood-Aware Agent**, "Situation Analysis" → **Situation Room**, entrypoint `app.py` → **Home.py** (required since Streamlit's classic multi-page mode derives the entrypoint's nav label from its filename with no supported override).
- Distinct, purposeful per-page icons (🧭 Flood-Aware Agent, 📋 Policy Advisor, 🗺️ Situation Room), with 🌊 reserved as the single primary brand mark rather than reused everywhere.
- Page-appropriate rotating progress messages: Policy Advisor now shows guidance-flavored messages ("Reviewing government guidance...", "Searching official documents...") instead of GIS-flavored ones.

### Fixed

- **Chat input positioning.** `st.chat_input()` was called inside a bordered `st.container()`, which forces Streamlit's inline (non-bottom-pinned) positioning — confirmed against Streamlit's own source. Fixed by keeping `chat_input()` at true root scope.
- **Message rendering-order inconsistency.** The newly-submitted user message was rendered through a separate, one-off code path instead of the same history-rendering pass as every prior message — two independent writers to the same container meant visual order depended on incidental call timing. Fixed by appending to session state first, then rendering the entire history through a single `render_history()` call per run.
- **Risk/confidence badges shown on Policy Advisor.** Conceptually wrong for pure policy questions. Added a `show_risk_badges` parameter to the shared chat component; Policy Advisor passes `False`. Display-only — `Decision`/API response shape untouched.
- **Village selector UX.** Previously defaulted to an unlabeled "(manual entry)" option and always showed redundant manual fields even when a real village was selected. Fixed: real `index=None` placeholder ("Select a village..."), manual fields only appear behind an explicit "Other / not listed" choice, Province remains the sole always-visible optional field.
- **Two real grounding/specificity bugs surfaced only by live UI testing, requiring multiple rounds of empirical refinement:**
  - **Shelter-specific questions on absent evidence deterministically 503'd.** Root cause (confirmed via a captured live backend log): `DecisionActionGroundingError`'s retry-correction message told the model to "not center the action on" the absent category — but when the user's own question is specifically about that category, the model has almost no way to answer honestly without using flagged vocabulary, causing deterministic 3-attempt retry exhaustion. Fixed by softening the correction message to explicitly permit honestly naming the absent topic while still banning invented specifics.
  - **A second, distinct specificity failure on topic-focused answers.** `DecisionSpecificityError` separately rejected responses correctly, narrowly focused on one topic (e.g. policy) without repeating unrelated present-but-off-topic figures (e.g. GIS/weather numbers irrelevant to a policy question) — the existing "honest absence" exemption only covered *entirely-absent* categories, not *present-but-uncited* ones. Generalized to its true, simpler, more robust form: any figure-bearing category is exempt if never cited/referenced anywhere in the decision, regardless of whether it's entirely absent or merely off-topic. Re-verified genuine evidence-ignoring detection remains intact.
  - Two golden-set test assertions were themselves found to be too strict during this work (rejecting the literal word "shelter", or requiring an exact absence-category match) and were corrected to test the real intended standard.

### Verified

- Full suite: 275 passed, 2 skipped. Full golden set: 21/21 passing, including 3 consecutive stable runs of both newly-fixed scenarios before final confirmation.
- Extensive live, real-UI, real-backend end-to-end verification: the exact shelter question that previously failed repeatedly now returns a real, honest, non-fabricating answer with no 503; policy follow-ups correctly cite real guidance without repeating unrelated figures; all visual fixes confirmed live after a full process restart.
- One pre-existing, unrelated golden test (`test_shelter_recommendation`) intermittently failed on exact citation-string phrasing, unconnected to any change made — confirmed non-reproducing on immediate re-run.

### Notes

- A brief content-dimming visual during Streamlit's rerun transition was investigated and confirmed to be Streamlit's own standard framework-level rerun styling, present in every Streamlit app — not a defect in this project's code. Deliberately left as-is.
- Situation Room's map still shows only a dataset-level bounding box with an honest "not configured" notice — real per-record `spatial_bounds` configuration remains a small, low-priority deferred item.
- `uvicorn --reload`'s default file-watching includes the entire project directory, which can trigger an unrelated Windows `multiprocessing`/`anyio` reload-watcher crash when only frontend files change. Fix: scope watching with `--reload-dir backend`.

---

## Hotfix 14.4 – Regional GIS Dataset Extraction (2026-08-01)

### Added

- Added `scripts/extract_regional_gis_data.py`: a one-time, standalone extraction script (not part of the request path) producing `data/gis/osm/raw/swat-region.osm.pbf` and `data/gis/worldpop/raw/swat-region_ppp_2025.tif` — spatially clipped, reference-complete regional extracts of the Pakistan-wide source files, buffered 0.2° (~20-22 km) around `DEFAULT_SWAT_BOUNDING_BOX` to avoid clipping anything analytically relevant near the boundary. Uses `pyosmium`'s `FileProcessor(...).with_locations()` + `BackReferenceWriter(remove_tags=False)` for a reference-complete spatial extract (no dangling node/way/relation references, no tags stripped) and `rasterio.mask.mask(crop=True)` for the raster clip. Original Pakistan-wide files are untouched and remain in the repository.
- Added `scripts/compare_regional_gis_accuracy.py`: a read-only validation script proving the regional extract is analytically equivalent to the original before trusting it in production.

### Fixed

- **Deployment-blocking cold-start latency.** `configure_graph_dependencies()`'s eager GIS warm-up previously parsed the entire Pakistan-wide OSM PBF (147.2 MiB) and WorldPop raster (134.9 MiB) at every application startup, even though the application only ever analyzes the Swat region — a real liability for deployment, since every real user's first visit (and every cold start after a hosting platform idles the server) would face this same multi-minute wait, not just local development. `graph_dependencies.py` now points at the regional extracts instead.
- Also updated `scripts/manual_chat.py`'s hardcoded paths to match, keeping the dev script consistent with production.

### Verified

- **Extraction accuracy:** direct side-by-side comparison (Mingora, 34.7700/72.3600, major severity) between the original Pakistan-wide files and the regional extract showed every metric bit-for-bit identical — river geometry (type, length to 2 decimal places, vertex count, bounds), affected area, population exposure, population density, WorldPop cell count, and all seven infrastructure categories (roads, bridges, schools, hospitals, clinics, police, fire stations).
- **Real startup time:** measured 39 seconds from `"Waiting for application startup"` to `"Application startup complete"` — down from the previous 5–6 minutes, an ~88–90% reduction.
- **Real production path:** live dashboard verification post-swap confirmed GIS analysis (`gis:GISDomainService` citation, real population/infrastructure reasoning) works correctly through the actual `/conversation` request path, not just in the isolated comparison script — confirmed for a real village at MODERATE severity.
- File size reduction: OSM PBF 147.2 MiB → 4.2 MiB (~97.1%); WorldPop raster 134.9 MiB → 2.0 MiB (~98.5%).

### Notes

- This directly resolves the real deployment concern this hotfix was scoped to address: a live user visiting the deployed app will now face a well-under-a-minute cold start, not several minutes.
- Original Pakistan-wide files and both new scripts remain in the repository — no data was deleted, only additional, smaller, regionally-scoped files were created alongside the originals.
- This closes the last known pre-deployment infrastructure concern. Project is now ready for Sprint 15 (deployment) or the planned React frontend work, per priority.

---

## [1.3.1] - 2026-07-29

---

## Hotfix – Live Verification & Reasoning-Quality Hardening (2026-07-29)

### Context

Following Sprint 13's automated verification, this session performed live,
adversarial manual testing of the full conversational pipeline
(`scripts/manual_chat.py`) against real production tools and real evidence
data for the first time. This surfaced several defects invisible to mocked
test coverage, and led to a substantive reasoning-quality improvement
beyond Sprint 13's original scope.

---

### Hotfix 1 — Dataset Catalog Provenance Crash

#### Fixed

- Fixed a real `AttributeError` in `DatasetEvidenceMapper.to_graph()`
  (`graph/mappers/configured_data_mappers.py`), which assumed
  `DatasetCatalogDTO` carried PDF-document provenance fields
  (`document_name`, `page_number`, `section`) that do not exist on it.
  Silently caught by Sprint 12's graceful tool-failure degradation in
  production, meaning Dataset citations were missing from every real
  recommendation without any visible error.
- Rebuilt citation format from real `DatasetMetadata`/`DatasetStatistics`
  fields (`name`, `version`, `source`) instead.

#### Verified

- Confirmed live in `manual_chat.py`: real dataset citations now appear
  in production output (e.g. `"Flood-Aware production villages:v1.0.0
  (source: Flood-Aware checked-in dataset: villages.csv)"`).

---

### Hotfix 2 — RAG Citation Corruption

#### Fixed

- Fixed `SemanticChunker._is_heading()` (`rag/semantic_chunker.py`)
  incorrectly classifying numeric table rows (e.g. `"450.00 Lai Nullah"`)
  as document section headings, corrupting downstream `Citation.section`
  values with concatenated table data.
- Strengthened the numbered-heading heuristic to reject multi-number,
  number-dominant lines while preserving legitimate numbered headings
  (`"1. Introduction"`, `"3.2 Evacuation Procedures"`, `"12) Overview"`).
- Rebuilt the persistent Chroma government-knowledge index
  (`scripts/build_government_index.py`) to purge previously-corrupted
  chunks (4 documents, 1,384 chunks re-indexed).

#### Verified

- Confirmed live: previously garbled `National_Disaster_Management_Plan`
  citations now render as clean `document:page` references.

---

### Hotfix 3 — Developer Tooling & Observability

#### Added

- Added `scripts/manual_chat.py`: a real, end-to-end interactive
  conversation script composing real Village/Shelter/DatasetCatalog/GIS/
  Knowledge tools with deterministic Weather/Forecast stand-ins, for live
  qualitative verification ahead of Sprint 14.
- Added `ExtraFieldsFormatter` (`config/logging.py`), rendering structured
  `log_event` fields (node, failure_type, duration_ms, etc.) in console
  output — previously captured but invisible under the default formatter.

#### Fixed

- Fixed `conversation/__init__.py` re-exporting submodule names instead of
  the actual `ConversationOrchestrator`/`ConversationSessionStore`/
  `ConversationTurn`/`ConversationSession` classes.

---

### Feature — Reasoning Specificity

#### Added

- Added `_key_figures()` (`decision/prompt_builder.py`), surfacing real
  quantitative evidence values (discharge, population exposed,
  infrastructure count, rainfall, shelter capacity, per-village
  population) directly in the prompt as a labeled "Key quantitative
  figures" section.
- Added a SPECIFICITY instruction to `PromptBuilder._SYSTEM_INSTRUCTIONS`
  with an explicit weak/strong contrast example, requiring
  `risk_assessment.rationale` and reasoning to incorporate real evidence
  figures rather than generic boilerplate.
- Added `DecisionSpecificityError` and `DecisionParser._validate_specificity`,
  enforcing that generated reasoning engages with real quantitative
  evidence when flood-severity-relevant figures are available.

#### Fixed (post-deployment corrections, same session)

- **Citation/figure-label collision:** the "Key quantitative figures"
  section's dict-key labels (e.g. `"village.Kabal.population"`) were
  mistaken by the model for valid citations, causing repeated
  `DecisionGroundingError` and, in one case, full retry-budget
  exhaustion. Fixed with an explicit prompt boundary distinguishing
  reasoning-only figure labels from the closed citation vocabulary.
- **Retry-with-feedback resilience upgrade:** rather than patch each new
  invented citation-format pattern individually (a second, structurally
  different hallucination — an invented `"type:entity_name"` hybrid
  format — was found immediately after the first fix), implemented a
  general self-correction mechanism. `DecisionGroundingError` now carries
  `invalid_references`; on a grounding failure, the retry loop appends the
  model's invalid response plus a targeted correction message naming the
  exact bad citations, rather than resending an identical prompt. Scoped
  strictly to `DecisionGroundingError` retries; all other failure types
  (timeout, rate limit, provider unavailable, non-grounding validation)
  retry unchanged, within the existing retry budget.
- **Over-broad enforcement correction:** `_validate_specificity` originally
  required citing figures from the full `_key_figures()` set, incorrectly
  forcing citation of bare village population counts (context, not flood
  evidence) even when a model's honest, evidence-free "no flood risk"
  response was otherwise correct — found via golden-set regression
  (`test_multiple_villages`). Split into `_key_figures()` (unchanged,
  full set, prompt display only) and a new, narrower
  `_flood_severity_figures()` (forecast/GIS/weather/shelter-capacity
  only, excludes village population) used solely for validation
  enforcement.

#### Verified

- Full test suite: 256 passed, 1 skipped.
- Full golden set (16 real-API scenarios, including 1 new specificity
  golden test): 16/16 passing.
- Live multi-turn manual verification: retry-with-feedback mechanism
  observed recovering from a real grounding failure in production without
  crashing or exhausting the retry budget; evidence-reuse and no-crash
  guarantees held across multiple real follow-up questions.

### Notes

- **Known limitation, deferred:** GIS evidence collection (real OSM/
  WorldPop parsing over the full Pakistan dataset) measured at 30s–4+
  minutes per fresh-evidence turn in live testing. No loading-state UX
  exists yet to communicate this to a user. Confirmed as a hard
  requirement for Sprint 14, not optional polish — real measured
  latencies now available to inform that design.
- No changes to `evidence_reference_index.py`, `models.py`, or graph
  routing/aggregation logic.
- No dashboard, chat UI, or deployment work — out of scope for this
  session.
- All fixes verified via both automated tests and live, real-API manual
  testing — not test-suite-only verification.
- Ready for Sprint 14 – Streamlit Dashboard.

---

## [1.3.0] - 2026-07-28

---

## Sprint 13 – Multi-Turn Conversation & Follow-Up Questions (2026-07-28)

### Sprint 13.1 — Conversation State Model

#### Added

- Added `backend/app/conversation/` package with immutable, strict Pydantic contracts: `ConversationTurn` (request context, active evidence bundle, resulting decision, timestamp) and `ConversationSession` (ordered turn history, keyed by UUID).
- Added `ConversationSessionStore`, an async-safe in-memory session store guarded by `asyncio.Lock`, with no persistence layer (explicit v1.0 scope decision).

---

### Sprint 13.2 — Deterministic Evidence-Reuse Policy

#### Added

- Added `requires_new_evidence()`, a pure function determining whether a follow-up requires fresh graph execution based solely on whether coordinates, village, district, or province changed from the immediately preceding turn — no NLP/intent classification.
- Added focused unit tests covering first-turn, identical-context, changed-location, and partial/unspecified-context scenarios.

---

### Sprint 13.3 — Conversation-Aware Prompting

#### Added

- Extended `PromptBuilder.build()` with an optional, backward-compatible `history` parameter (default empty), rendering prior turns' request text and recommendation summaries only — never prior evidence — preserving Sprint 11's grounding guarantees unchanged when history is empty.
- Added an explicit system-prompt instruction: conversation history is continuity context only; all grounding and citation rules apply exclusively to the current evidence bundle.

---

### Sprint 13.4 — Conversation Orchestration

#### Added

- Added `ConversationOrchestrator`, coordinating session lookup, evidence-reuse decisions, graph execution, and decision-agent invocation without owning graph or prompt logic itself.

#### Fixed

- Eliminated a redundant duplicate LLM call on fresh-evidence turns: the graph's own `RecommendationNode`-produced `Decision` is now retained directly on `GraphState` (new `decision: Decision | None` field, mirroring the existing `forecast_result`/`forecast` canonical-plus-projection pattern) and reused by the orchestrator, instead of invoking the decision agent a second time.
- Corrected a dependency-direction violation introduced mid-sprint: `backend/app/decision/` briefly imported `backend/app/conversation/` directly, inverting this project's established Clean Architecture layering. Replaced with a narrow structural `ConversationTurnLike` protocol in `decision/protocols.py`; `decision/` no longer imports from `conversation/` anywhere.
- Added explicit, non-silent handling for graph fallback without a canonical decision: `ConversationOrchestrator` raises `DecisionGenerationError` rather than fabricating or retrying, with a dedicated regression test proving the graph runs exactly once and the decision agent is never separately invoked in this case.

---

### Sprint 13.5 — Multi-Turn Verification

#### Added

- Added 6 scripted multi-turn test scenarios: 3 orchestration-level tests using injected spies (call-count and evidence-identity verification), and 3 real, non-mocked golden-set tests (`backend/tests/golden/test_conversation_golden_set.py`, gated behind `RUN_GOLDEN_SET=1`) exercising the real OpenAI provider and real graph runtime against deterministic tool boundaries.

#### Verified

- Same-context follow-ups reuse evidence with zero additional tool invocations across all 7 evidence tools; changed-context follow-ups correctly trigger exactly one fresh round of all 7 tool invocations.
- Real grounded decisions across 3 consecutive real follow-ups, each independently citation-validated against its active evidence bundle.
- No cross-turn evidence leakage: a real second-turn decision for a different village contains no reference to the first turn's village-specific evidence.
- Real prompt history threading verified via `wraps=`-spied `PromptBuilder.build()`: third-turn history contains exactly the first two turns' summaries, in order.
- Full test suite (247 tests) passes with zero regressions.

### Notes

- No changes to `decision/parser.py`, `evidence_reference_index.py`, or `decision/models.py`.
- No Urdu/multilingual work — English-only, per project plan.
- No persistent/database-backed session storage — in-memory only, explicit v1.0 scope.
- No Streamlit/chat UI — deferred to Sprint 14.
- Sprint 13 completed.

---

## [1.2.0] - 2026-07-28

---

## Sprint 12 – Reliable Multi-Tool Agent Behavior (2026-07-28)

### Sprint 12.1 — Routing Audit & Baseline Verification

#### Added

- Added `backend/tests/graph/test_tool_invocation_routing.py`, exercising the real `GraphRuntime` and `FloodSeverityRoutingPolicy` (not mocked) against five representative query-intent scenarios.
- Added `docs/routing-decision-table.md`, documenting verified current routing behavior for FYP System Design reference.

#### Verified

- Confirmed current routing is deterministic and severity-based, computed after forecast/GIS evidence collection — not query-intent-based.
- Confirmed `UserRequest`'s text and location fields are not consulted by `FloodSeverityRoutingPolicy`; forecast-only, GIS-impact, shelter, and policy-question queries with identical severity follow identical tool paths today.
- Documented this explicitly as current, tested baseline behavior; query-intent-based tool selection identified and recorded as a scoped future design decision (TODO marker in test suite), not undertaken this sprint.

---

### Sprint 12.2 — Graceful Tool-Failure Degradation

#### Added

- Added `_record_tool_failure`, a shared helper wrapping genuine evidence-tool dependency failures into a recoverable, immutable `ErrorInfo` appended to graph state, with structured WARNING-level logging.
- Wrapped all seven evidence node tool calls (`Weather`, `Forecast`, `GIS`, `Village`, `Shelter`, `DatasetCatalog`, `GovernmentKnowledge`) in this shared failure-recovery path.

#### Improved

- `GraphRuntime`'s trace-recording now distinguishes `FAILED` (genuine dependency error, `ErrorInfo` recorded) from `SKIPPED` (node did not run) at the point of execution, rather than only inferring skips at trace finalization.

#### Verified

- A single failing evidence tool no longer aborts the graph; other evidence sections, aggregation, and the recommendation step complete normally around the failure.
- Full existing test suite (232 tests at this point) passes with all direct node-failure tests updated to assert recoverable-error behavior instead of propagated exceptions.

---

### Sprint 12.3 — Precondition-Skip Handling

#### Added

- Extended `GraphRuntime`'s trace wrapper to classify any node returning its input state unchanged (identity-based, via `model_copy`-free passthrough) as `NodeStatus.SKIPPED`, reusing the same status semantics already used for severity-based routing skips rather than introducing a parallel mechanism.
- `WeatherNode`, `ForecastNode`, `GISAnalysisNode`, and `GovernmentKnowledgeNode` now return unchanged state (with an INFO-level `graph_evidence_node_skipped` log event) instead of raising an uncaught exception when a required precondition (coordinates, request text) is absent.

#### Fixed

- Corrected an incidental pre-existing mislabeling: `Dormant*` placeholder nodes were previously recorded as `COMPLETED`; they now correctly show as `SKIPPED`, since they always return state unchanged by design.

#### Verified

- A real graph run for a coordinate-less policy/knowledge-only query completes end-to-end without crashing; weather, forecast, and GIS correctly marked `SKIPPED` (not `FAILED`); knowledge, dataset, and recommendation complete normally.
- Confirmed the skip-detection mechanism is identity-based (`result is state`), not value-equality-based, so a genuine successful tool call that legitimately returns an empty result cannot be misclassified as skipped.

---

### Sprint 12.4 — Concurrency Verification

#### Added

- Added a concurrent-execution regression test running two distinct real graph states through one shared `GraphRuntime` instance via `asyncio.gather`.

#### Verified

- Confirmed no shared-state leakage between concurrent requests; each result's evidence corresponds correctly to its own input, consistent with `GraphState`'s frozen/immutable design.

### Notes

- No changes to GIS, Forecast, Weather, or RAG subsystem internals — only their graph-node boundaries.
- No changes to `prompt_builder.py`, `parser.py`, or any Sprint 11 grounding/reasoning file.
- Query-intent-based tool selection remains explicitly out of scope, documented as a future design decision.
- No dashboard, chat, or deployment work — out of scope for this sprint.
- Full test suite (234 tests) passes.
- Sprint 12 completed.
- Ready for Sprint 13 – Multi-Turn Conversation & Follow-Up Questions.

---

## [1.1.0] - 2026-07-28

---

## Sprint 11 – LLM Reasoning & Grounded Recommendation (2026-07-28)

### Sprint 11.1 — Grounded Prompt & Citation Enforcement

#### Added

- Added `EvidenceReferenceIndex`, computing the closed vocabulary of valid citation strings from an `EvidenceBundle` (provenance-level, knowledge citations, dataset provenance, named villages/shelters).
- Rebuilt `PromptBuilder` system instructions to enforce: exact-match citation vocabulary, non-empty grounding when evidence exists, explicit conflict-handling with confidence downgrade, explicit naming of entirely-absent evidence categories in `missing_evidence`, single-source confidence capping, and preference for named entities over generic tool-level references.
- Added `DecisionGroundingError`, validated in `DecisionParser` against `EvidenceReferenceIndex`, rejecting decisions that cite evidence absent from the bundle.
- Added a strict-schema transform (`_to_strict_openai_schema`) in the OpenAI provider adapter, recursively enforcing `additionalProperties: false` and complete `required` arrays across `Decision`'s nested schema, resolving an OpenAI strict-structured-output rejection.
- Registered `DecisionGroundingError` as a retryable/transient failure, reusing the existing retry/backoff budget rather than a new fallback path.

#### Improved

- Clarified prompt instructions so evidence categories listed as "entirely absent" are never mistaken for citable references, preventing false-positive grounding rejections.

---

### Sprint 11.2 — Golden-Set Evaluation

#### Added

- Added `backend/tests/golden/`, a real (non-mocked) OpenAI evaluation suite of 12 hand-crafted evidence scenarios: severe forecast+GIS, calm baseline, conflicting severity, empty bundle, shelter recommendation, knowledge-only, extreme exposure, weather-only, multiple villages, capacity shortfall, duplicate evidence, and a full multi-section bundle.
- Added `build_openai_decision_provider()` production factory (`backend/app/decision/dependencies.py`), constructing a live `OpenAIDecisionProvider` from application settings.
- Added `backend/app/decision/settings.py` for decision-provider configuration.
- Added a shared `_all_references()` test helper, consolidating citation/evidence-reference aggregation across golden-set tests to eliminate inconsistent partial-field checks.
- Gated the golden-set suite behind `RUN_GOLDEN_SET=1` to avoid unintended API cost during normal test runs.

#### Improved

- Replaced brittle exact-substring and literal-keyword test assertions with structural, grounding-aware, and keyword-tolerant checks, addressing false failures caused by legitimate LLM wording variance under `temperature=0`.

#### Verified

- All 12 golden-set scenarios pass consistently across repeated runs against the live OpenAI API.
- Grounding validation correctly rejects citations not present in the evidence bundle and correctly accepts valid entity-level, tool-level, and document-level citations.
- Confidence is correctly downgraded in the presence of detected evidence conflicts.
- Absent evidence categories are correctly surfaced in `missing_evidence` rather than fabricated.

---

### Sprint 11.3 — Fallback Regression & Housekeeping

#### Added

- Added `test_provider_raises_after_persistent_rate_limit`, confirming `OpenAIDecisionProvider` exhausts its retry budget and raises correctly under persistent transient failure.
- Added `test_recommendation_node_maps_decision_error_to_fallback`, confirming `RecommendationNode` maps any `DecisionError` to `DecisionFallbackMapper.unavailable()`.

#### Changed

- Renamed `backend/app/graph/nodes/skeletons.py` to `backend/app/graph/nodes/evidence_nodes.py` to accurately reflect its contents (fully-implemented production node classes, not stubs), matching existing descriptive module-naming conventions in `graph/`. No behavioral change; import updated at the package boundary (`graph/nodes/__init__.py`) only.

#### Verified

- Full existing test suite (225 tests) passes unchanged after the rename and all Sprint 11 additions.
- Reasoning-trace content (`Decision.reasons`) confirmed present and grounded in returned decisions; confirmed intentionally excluded from structured logs, consistent with this project's existing safe-logging discipline (no prompts, evidence, or full model output in logs).
- Manual qualitative review of real LLM output across three representative scenarios (severe forecast+GIS, shelter recommendation, conflicting evidence) confirmed coherent, non-generic, evidence-specific reasoning and recommendations.

### Notes

- No changes to GIS, Forecast, Weather, or RAG subsystems.
- No changes to graph routing, evidence aggregation, or dataset/service layers.
- No dashboard, chat, or deployment work — out of scope for this sprint.
- LLM decision boundary is now grounded, citation-validated, conflict-aware, and regression-tested against both mocked failure modes and live API behavior.
- Sprint 11 completed.
- Ready for Sprint 12 – Reliable Multi-Tool Agent Behavior.

---

## [1.0.0] - 2026-07-27

---

## Sprint 10 – LangGraph Decision Agent (2026-07-27)

### Sprint 10.1 — Graph Definition

#### Added

- Added LangGraph foundation.
- Added immutable graph state.
- Added graph runtime.
- Added graph builder.
- Added graph container.
- Added dependency injection boundaries.
- Preserved the existing sequential runtime as the production default.

---

### Sprint 10.2 — Evidence Infrastructure

#### Added

- Added production Weather Tool node.
- Added Forecast Tool node.
- Added GIS Flood Analysis node.
- Added Village Tool node.
- Added Shelter Tool node.
- Added Dataset Catalog node.
- Added Government Knowledge Tool node.
- Added immutable graph node interfaces.

---

### Sprint 10.2.4 — Architecture Cleanup

#### Improved

- Simplified graph composition.
- Improved dependency boundaries.
- Removed unnecessary coupling.
- Standardised graph node interfaces.
- Improved maintainability of graph execution.

---

### Sprint 10.3 — Conditional Routing

#### Added

- Added deterministic conditional routing.
- Added forecast severity routing.
- Added graph branching rules.
- Added routing policies for evidence execution.

---

### Sprint 10.4 — Evidence Aggregation

#### Added

- Added immutable evidence aggregation.
- Added evidence provenance.
- Added duplicate detection.
- Added evidence conflict handling.
- Added execution trace support.
- Added unified evidence container.

---

### Sprint 10.5 — LLM Decision & Recommendation Agent

#### Added

- Added structured LLM decision layer.
- Added decision contracts.
- Added prompt builder.
- Added response parser.
- Added provider abstraction.
- Added OpenAI provider adapter.
- Added recommendation mapping.

---

### Sprint 10.5.1 — LLM Architecture Refinement

#### Improved

- Improved provider dependency boundaries.
- Improved prompt version metadata.
- Improved naming consistency.
- Improved documentation.
- Simplified provider integration.

---

### Sprint 10.6 — Failure Recovery & Resilience

#### Added

- Added request timeout handling.
- Added transient retry mechanism.
- Added circuit breaker.
- Added typed provider failures.
- Added provider health monitoring.
- Added deterministic fallback recommendations.

---

### Sprint 10.7 — Observability & Production Hardening

#### Added

- Added execution correlation context.
- Added structured runtime logging.
- Added timing utilities.
- Added metrics abstraction.
- Added runtime version metadata.
- Added provider health reporting.
- Added production dataset bootstrap configuration.
- Added automatic startup dataset initialization.

#### Improved

- Improved runtime dependency injection.
- Improved production dataset compatibility.
- Improved nullable production dataset handling.
- Preserved explicit runtime configuration for tests.

---

### Verified

- LangGraph graph compilation verified.
- Evidence pipeline verified.
- Conditional routing verified.
- Evidence aggregation verified.
- LLM provider abstraction verified.
- Failure recovery verified.
- Observability verified.
- Swagger UI verified.
- OpenAPI specification verified.
- Production dataset loading verified.
- `/health` endpoint verified.
- `/shelters` endpoint verified.
- `/datasets/catalog` endpoint verified.
- Dataset service suite passed (27 tests).

---

### Notes

- Legacy sequential runtime remains the production default.
- LangGraph runtime introduced without breaking existing runtime.
- Deterministic evidence pipeline established.
- Production-ready LLM decision boundary completed.
- Sprint 10 completed.
- Ready for Sprint 11 – LLM Reasoning & Grounded Recommendation

---

## [0.9.6] - 2026-07-26

---

## Sprint 9.6 – GIS Flood Analysis Tool (2026-07-26)

### Added

- Added deterministic GIS processing package.
- Added GIS configuration and shared type aliases.
- Added RasterCache with deterministic lifecycle management.
- Added raster utility helpers.
- Added DEM loader.
- Added deterministic Flood Zone Generator.
- Added WorldPop loader.
- Added Population Exposure Calculator.
- Added OSM loader.
- Added Infrastructure Impact Calculator.
- Added immutable FloodEvidence model.
- Added FloodEvidenceBuilder.
- Added comprehensive GIS processing tests.
- Added Flood Evidence tests.
- Added GIS processing documentation.

### Improved

- Established deterministic GIS processing pipeline.
- Established immutable spatial evidence generation.
- Enforced strict separation between GIS processing and AI Runtime.
- GIS evidence now aggregates existing forecast and spatial facts without recalculation.
- Improved documentation describing GIS architecture and AI-first evidence generation.

### Verified

- DEM processing verified.
- Flood zone generation verified.
- Raster cache verified.
- Raster utilities verified.
- Population exposure verified.
- OSM infrastructure extraction verified.
- Infrastructure impact verified.
- Flood evidence generation verified.
- GIS unit tests passed.
- Pytest suite passed.

### Notes

- No AI Runtime changes.
- No Planner changes.
- No Tool Registry changes.
- No Agent orchestration changes.
- No FastAPI changes.
- No Forecast Tool changes.
- No Government Knowledge Tool changes.
- No Runtime execution changes.
- GIS Flood Analysis Tool completed.
- Sprint 9.6 frozen.
- Ready for Sprint 9.7 – AI Runtime Integration.

--- 

## [0.9.5] - 2026-07-25

---

## Sprint 9.5 – GloFAS Forecast Tool (2026-07-25)

### Added

- Added dedicated Forecast package.
- Added immutable forecast domain models.
- Added NetCDF Forecast Parser.
- Added Forecast Mapper.
- Added GloFAS Forecast Tool.
- Added Snapshot Locator.
- Added Forecast Settings.
- Added Forecast exception hierarchy.
- Added forecast ingestion pipeline.
- Added standalone forecast verification script.
- Added comprehensive unit tests.
- Added ingestion tests.

### Improved

- Snapshot discovery extracted into dedicated SnapshotLocator.
- Forecast Tool now depends on SnapshotLocator instead of filesystem traversal.
- Parser now validates required provenance metadata.
- Parser now fails fast when required metadata is missing.
- Forecast ingestion now writes request provenance into downloaded NetCDF snapshots.
- Forecast Tool architecture simplified into:
  - Tool
  - Snapshot Locator
  - Parser
  - Mapper
- Improved separation between ingestion, discovery, parsing, and mapping.

### Verified

- Forecast ingestion verified successfully.
- Local snapshot verification completed successfully.
- Parser metadata validation verified.
- Snapshot discovery verified.
- Unit tests passed.
- Pytest suite passed.
- Forecast verification script passed.

### Notes

- No AI Runtime changes.
- No Planner changes.
- No Registry changes.
- No Decision Engine changes.
- No Weather Tool changes.
- No Government Knowledge Tool changes.
- No Runtime execution changes.
- No FastAPI changes.
- No Agent orchestration changes.
- Forecast Tool completed.
- Sprint 9.5 frozen.
- Ready for Sprint 9.6 – GIS Flood Analysis Tool.

---

## [0.9.4] - 2026-07-24

---

## Sprint 9.4 – Weather Tool (2026-07-24)

### Added
- Introduced isolated Weather Tool package.
- Added OpenWeatherMap client using httpx.
- Added immutable WeatherRequest and WeatherResult models.
- Added WeatherMapper for provider-to-domain translation.
- Added WeatherSettings with environment-based configuration.
- Added Weather-specific exception hierarchy.
- Added standalone WeatherTool service.
- Added comprehensive unit tests.
- Added standalone live verification script.
- Added Weather Tool documentation.

### Improved
- Added ownership-aware HTTP client cleanup.
- Added configurable weather units through settings.
- Simplified Weather Tool tests for improved readability.
- Removed static-analysis warnings.

### Verified
- Live OpenWeatherMap verification completed successfully.
- All unit tests passed.
- All pytest suites passed.

---

## [0.9.3] - 2026-07-24

---

### Added

#### Sprint 9.3 – Government Knowledge Engine (RAG Tool)

##### Sprint 9.3.0 – Government Knowledge Base

- Added Government Knowledge Engine package
- Added Government document loader
- Added PDF cleaning pipeline
- Added semantic chunking pipeline
- Added OpenAI embedding service
- Added Chroma persistent vector store
- Added production Government Retriever
- Added Knowledge Tool
- Added prompt builder
- Added response generator
- Added immutable RAG models
- Added framework-independent RAG protocols
- Added explicit RAG configuration

##### Sprint 9.3.1 – Government Knowledge Evaluation

- Added isolated evaluation framework
- Added Benchmark Loader
- Added Retrieval Metrics
- Added Citation Checker
- Added Metrics Aggregator
- Added Evaluation Runner
- Added Evaluation Report Writer
- Added evaluation CLI
- Added benchmark validation tests
- Added evaluation integration tests
- Added evaluation JSON report generation
- Added evaluation Markdown report generation

##### Sprint 9.3.2 – Benchmark Synchronization

- Added benchmark synchronization utility
- Added automatic benchmark chunk-id synchronization
- Added automatic benchmark citation synchronization
- Preserved all human-authored benchmark metadata
- Added documented evaluation workflow

### Changed

- Government Knowledge Engine now uses a single shared `OPENAI_API_KEY`.
- Persistent Chroma index is rebuilt using the offline indexing pipeline.
- Benchmark maintenance is now automated after rebuilding the knowledge base.

### Notes

- No AI Runtime changes
- No Planner changes
- No Registry changes
- No Decision Engine changes
- No Weather Tool changes
- No Runtime execution changes
- No FastAPI changes
- No Agent orchestration changes
- Production runtime remains isolated from evaluation
- Government Knowledge Engine completed
- Evaluation pipeline completed
- Benchmark synchronization completed
- Sprint 9.3 frozen
- Ready for Sprint 9.4 – Weather Tool

---

## [0.9.2] - 2026-07-24

---

### Added

#### Sprint 9.2 – Runtime Tool Integration

##### Sprint 9.2.0 – Production Dataset Projection

- Added repository-boundary production dataset projection
- Added explicit projection for production village datasets
- Added explicit projection for production shelter datasets
- Preserved immutable production CSV files
- Preserved frozen DTO contracts
- Preserved Application Layer contracts
- Added production dataset projection tests
- Enabled production datasets to be consumed without modifying services or DTOs

##### Sprint 9.2.1 – Runtime Integration Validation

- Added end-to-end runtime integration tests
- Validated AIRuntime execution against production datasets
- Validated VillageTool execution
- Validated ShelterTool execution
- Validated DatasetCatalogTool execution
- Verified ToolRegistry registration
- Verified sequential runtime execution
- Verified DecisionContext preservation
- Verified runtime failure handling for unknown tools
- Removed dependency on mocked runtime execution for integration validation

### Changed

- Runtime now executes against real production datasets
- Repository projection now adapts production CSV schema to frozen application contracts
- Runtime validation now exercises the complete execution pipeline

### Notes

- No Decision Engine changes
- No Planner changes
- No AIRuntime changes
- No Registry changes
- No Executor changes
- No Service changes
- No DTO changes
- No Use Case changes
- No Protocol changes
- No FastAPI changes
- No AI behavior changes
- Repository projection completed
- Runtime integration completed
- Architecture remains framework-independent
- Ready for Sprint 9.3 – RAG Knowledge Tool

---

## [0.9.0] - 2026-07-24

---

### Added

#### Sprint 9 – AI Runtime Infrastructure

##### Sprint 9.1 – Runtime Infrastructure

- Added framework-independent AI runtime package
- Added Tool Registry for runtime tool discovery
- Added immutable Tool Metadata contracts
- Added Runtime Tool Executor
- Added runtime lifecycle state definitions
- Added decision lifecycle state definitions
- Added execution-scoped memory
- Added deterministic Sequential Planner
- Added execution trace infrastructure
- Added runtime exception hierarchy
- Preserved complete framework independence

##### Sprint 9.1.5 – Runtime Composition

- Added immutable `AIRuntime` composition facade
- Composed Planner
- Composed Executor
- Composed Registry
- Composed Execution Memory
- Composed Execution Trace
- Established a stable runtime boundary between the Decision Engine and future LangGraph orchestration

### Changed

- ExecutionMemory now preserves chronological execution order.
- AI runtime infrastructure is now considered frozen.
- Future Sprint 9 work will build on this runtime instead of modifying it.

### Notes

- No business logic introduced
- No LangChain dependency
- No LangGraph dependency
- No LLM provider dependency
- No FastAPI dependency
- No repository changes
- No service changes
- No API changes
- Runtime infrastructure completed
- Stable architectural foundation established
- Ready for Sprint 9.2 – Runtime AI Tools

---

## [0.8.0] - 2026-07-23

---

### Added

#### Sprint 8 – AI Decision Layer

##### Sprint 8.1 – AI Layer Foundation

- Added dedicated AI package
- Established AI orchestration boundary
- Introduced AI package structure

##### Sprint 8.2 – AI Domain Models

- Added `DecisionRequest`
- Added `DecisionContext`
- Added `DecisionResult`
- Added `Recommendation`
- Added `RecommendationPriority`
- Added `ToolResult`
- Introduced immutable AI decision contracts

##### Sprint 8.3 – AI Tool Protocols

- Added `VillageToolProtocol`
- Added `ShelterToolProtocol`
- Added `DatasetCatalogToolProtocol`
- Added structural AI tool interfaces
- Preserved dependency inversion

##### Sprint 8.4 – AI Tool Implementations

- Added deterministic Village Tool
- Added deterministic Shelter Tool
- Added deterministic Dataset Catalog Tool
- Introduced immutable ToolResult generation
- Preserved framework independence

##### Sprint 8.5 – Decision Engine

- Added deterministic `DecisionEngine`
- Introduced immutable `DecisionContext` propagation
- Added request context preservation
- Added orchestration of AI tools
- Added placeholder recommendation generation
- Preserved Clean Architecture dependency direction

##### Sprint 8.6 – Decision Engine Tests

- Added contract-focused Decision Engine tests
- Verified tool invocation
- Verified request context propagation
- Verified ToolResult identity preservation
- Verified placeholder recommendation contract
- Verified failure propagation
- Decoupled tests from implementation details
- Prepared test suite for future LangGraph implementation

### Changed

- Introduced dedicated AI orchestration layer
- Added stable AI execution contract
- Established deterministic execution flow:

  Decision Engine
  → AI Tools
  → Application Use Cases
  → Services
  → Repositories

### Notes

- No business logic introduced
- No LLM integration
- No LangChain dependency
- No LangGraph dependency
- No FastAPI dependency
- No repository changes
- No service changes
- No API changes
- AI layer completed
- Ready for Sprint 9 – LangChain / LangGraph Integration

---

## [0.7.0] - 2026-07-23

---

### Added

#### Sprint 7 – Application Use Case Layer

##### Sprint 7.1 – Application Layer Foundation

- Added dedicated Application Use Case layer
- Established application-task orchestration boundary
- Introduced application use-case package structure

##### Sprint 7.2 – Use Case Protocols

- Added `ViewVillagesUseCaseProtocol`
- Added `ViewSheltersUseCaseProtocol`
- Added `ViewDatasetCatalogUseCaseProtocol`
- Introduced structural protocols for application tasks

##### Sprint 7.3 – Concrete Use Cases

- Added `ViewVillagesUseCase`
- Added `ViewSheltersUseCase`
- Added `ViewDatasetCatalogUseCase`
- Introduced thin orchestration layer between API and Services
- Preserved immutable DTO passthrough

##### Sprint 7.4 – Composition Providers

- Added `get_village_use_case()`
- Added `get_shelter_use_case()`
- Added `get_dataset_catalog_use_case()`
- Extended Composition Root to construct application use cases
- Preserved existing service composition

##### Sprint 7.5 – API Migration

- Migrated API endpoints to depend on use-case protocols
- API now invokes application use cases instead of services
- DTO-to-schema translation remains exclusively within the API layer
- Preserved endpoint behavior and response payloads

##### Sprint 7.6 – Application Layer Tests

- Added dedicated unit tests for application use cases
- Verified service delegation
- Verified immutable DTO passthrough
- Verified Application Layer isolation from FastAPI, repositories, and filesystem
- Added orchestration-layer architectural tests

### Changed

- API dependency flow now follows:

  API → Use Cases → Services → Repositories

- Application Layer now provides the stable orchestration boundary for future AI agents

### Notes

- No business logic introduced
- No repository behavior changed
- No service behavior changed
- No DTO changes
- No API response changes
- Clean Architecture dependency direction preserved
- Application Layer completed
- Ready for Sprint 8 – AI Decision Engine

---

## [0.6.4] - 2026-07-23

### Added

#### Sprint 6.2 – API Endpoints

- Added `GET /villages`
- Added `GET /shelters`
- Added `GET /datasets/catalog`
- Added dedicated API routers:
  - `villages.py`
  - `shelters.py`
  - `datasets.py`
- Added centralized router registration
- Added dependency injection through Composition Root
- Added endpoint response translation from DTOs to API schemas
- Added endpoint integration tests
- Added OpenAPI documentation for all dataset endpoints

### Changed

- Centralized API route registration
- Improved global exception registration
- Application exceptions now use the centralized exception handler
- OpenAPI now documents all dataset endpoints

### Testing

- Added endpoint integration tests
- Verified Swagger (`/docs`)
- Verified ReDoc (`/redoc`)
- Verified OpenAPI schema generation
- Verified global exception handling
- Verified dependency injection through application configuration

### Notes

- Sprint 6 completed
- API Layer completed
- Ready for Sprint 7

---

## [0.6.3] - 2026-07-23

### Added

#### Sprint 6.1.6 – Application Composition Root

- Added application composition root
- Added runtime dataset dependency configuration
- Added `configure_dataset_dependencies()`
- Added `get_village_service()`
- Added `get_shelter_service()`
- Added `get_dataset_catalog_service()`
- Added application-owned runtime `DatasetCatalogConfig`
- Introduced transport-independent dependency providers
- Added immutable DTO translation boundary between Services and API schemas
- Added `ApplicationError`
- Added `ApplicationConfigurationError`
- Composition providers now return service protocols instead of concrete implementations
- API schemas now translate DTOs using `from_dto()` methods
- Dataset catalog now exposes explicit `villages` and `shelters` summaries

### Changed

- Service layer no longer depends on API schemas
- Introduced DTO layer between Services and API
- Restored Clean Architecture dependency direction
- Application configuration now owns runtime dataset configuration
- Configuration failures now use `ApplicationConfigurationError`
- Dependency providers expose service abstractions instead of concrete classes

### Notes

- No API endpoints added
- No routers added
- No business logic introduced
- No repository behavior changed
- No dependency injection redesign
- No caching introduced
- No authentication introduced
- Composition Root completed
- Ready for Sprint 6.2 – API Endpoints

---

## [0.6.2] - 2026-07-22

### Changed

#### Sprint 6.1.1 – API Architecture Refinement

##### Clean Architecture

- Introduced an application DTO layer between Services and API schemas
- Restored one-way dependency flow from API → Services → Repository
- Removed all Pydantic model dependencies from the service layer
- Removed all FastAPI dependencies from the service layer
- Services now return immutable application DTOs instead of API response models

##### DTO Layer

Added immutable application DTOs:

- VillageDTO
- VillageListDTO
- ShelterDTO
- ShelterListDTO
- DatasetSummaryDTO
- DatasetCatalogDTO

##### API Schema Translation

- Added `from_dto()` translation methods to all API response models
- API schemas are now responsible only for transport serialization
- Moved DTO → API conversion entirely into the schema layer

##### Dataset Catalog

Refined dataset catalog contract.

Replaced positional summaries

(village_summary, shelter_summary)

with explicit named fields
villages
shelters

improving readability and eliminating ordering assumptions.

##### Testing

Updated service tests to validate:

- DTO generation
- API translation layer
- Named dataset catalog responses
- Service independence from transport models

### Notes

- Repository layer unchanged
- Dependency Injection unchanged
- Runtime behavior unchanged
- No business logic introduced
- No FastAPI endpoints added
- No routers added
- Architecture only

---

## [0.6.1] - 2026-07-22

### Added

#### Sprint 6.1 – API Contracts

- Added `VillageResponse`
- Added `VillageListResponse`
- Added `ShelterResponse`
- Added `ShelterListResponse`
- Added `DatasetSummaryResponse`
- Reused existing `SuccessResponse`
- Reused existing `BaseResponse`
- Reused existing `ErrorResponse`
- Reused existing `DatasetMetadata`
- Reused existing `DatasetStatistics`
- Added strict immutable Pydantic API contracts
- Refined `DatasetSummaryResponse` by renaming `dataset_metadata` to `metadata` for improved readability

### Notes

- No API endpoints added
- No routing added
- No dependency injection added
- No repository changes
- No service changes
- No business logic introduced
- API contracts only

---

## [0.5.3] - 2026-07-22

### Added

#### Sprint 5.4 – Service Tests

- Added integration-style service layer tests
- Verified CSVRepository loads DatasetTable correctly
- Verified GeoJSONRepository loads DatasetTable correctly
- Verified DatasetService delegates to repositories
- Verified VillageService composition
- Verified ShelterService composition
- Verified dependency factory construction
- Added negative validation tests
- Reused fixture datasets for repository/service integration testing

### Notes

- No production architecture changed
- No business logic introduced
- No repository behavior modified
- No service behavior modified
- Tests verify composition only

---

## [0.5.2] - 2026-07-22

### Added

#### Sprint 5.3 – Service Configuration / Dependency Wiring

- Added explicit dependency factory functions
- Added `create_dataset_service`
- Added `create_village_service`
- Added `create_shelter_service`
- Centralized repository and service construction
- Added reusable CSV repository construction helper
- Preserved explicit dependency injection
- Prepared architecture for future FastAPI endpoint wiring

### Notes

- No API endpoints added
- No business logic introduced
- No repository contracts modified
- No service contracts modified
- No filesystem access performed during construction
- All metadata and schemas remain caller supplied

---

## [0.5.1] - 2026-07-22

### Added

#### Sprint 5.2 – Service Implementations

- Added generic `DatasetService`
- Added `VillageService`
- Added `ShelterService`
- Implemented service composition using `DatasetTableRepositoryProtocol`
- Implemented repository delegation through `CSVRepository`
- Applied constructor dependency injection
- Preserved repository and service separation

### Notes

- No business logic introduced
- No repository changes
- No CRUD operations
- No caching
- No API endpoints added
- No LangGraph integration
- Services coordinate repository access only

---

## [0.5.0] - 2026-07-22

### Added

#### Sprint 5.1 – Service Contracts

- Added `DatasetServiceProtocol`
- Added `VillageServiceProtocol`
- Added `ShelterServiceProtocol`
- Introduced service-layer structural contracts
- Established separation between Service Layer and Repository Layer

### Notes

- No service implementations added
- No business logic introduced
- No repository changes
- No API changes
- No LangGraph integration
- Service layer now provides stable contracts for future implementations

---

## [0.4.7] - 2026-07-22

### Added

#### Sprint 4.8 – Repository Implementations

- Added concrete `CSVRepository`
- Added concrete `GeoJSONRepository`
- Implemented `DatasetTableRepositoryProtocol`
- Added repository validation workflows
- Added dataset loading through explicit repository configuration
- Reused `FileRepositoryConfig`
- Reused serialization contracts
- Reused CSV and GeoJSON validation infrastructure
- Completed the first concrete repository implementations for the data layer

### Notes

- Read-only repositories only
- No CRUD operations introduced
- No metadata inference
- No schema inference
- No identifier generation
- No business logic added
- No caching introduced
- Existing APIs remain unchanged

---

## [0.4.6] - 2026-07-22

### Added

#### Sprint 4.7 – Repository Protocol Refinement

- Added `DatasetTableRepositoryProtocol`
- Separated dataset-oriented repositories from entity-oriented repositories
- Refined repository protocol architecture
- Applied Interface Segregation Principle (ISP)
- Preserved existing entity repository protocols
- Prepared architecture for concrete repository implementations

### Notes

- No repository implementations added
- No CRUD logic introduced
- No identifiers invented
- No metadata or schema inference
- No filesystem access introduced

## [0.4.5] - 2026-07-22

### Added

#### Sprint 4.6 – Repository Configuration Contracts

- Added immutable `FileRepositoryConfig`
- Added explicit repository configuration contract
- Added repository path validation
- Added repository metadata validation
- Added repository schema validation
- Added repository file format validation
- Added repository configuration consistency checks

### Notes

- No repository implementations added
- No filesystem access introduced
- No metadata inference
- No schema inference
- Configuration is entirely caller-supplied

---

## [0.4.4] - 2026-07-22

### Added

#### Sprint 4.5 – Serialization Contracts

- Added CSV serialization between `DatasetTable` and CSV text
- Added CSV deserialization using explicit `DatasetSchema`
- Added GeoJSON serialization between `DatasetTable` and `FeatureCollection`
- Added GeoJSON deserialization using explicit `DatasetSchema`
- Added deterministic serialization validation
- Reused existing GIS GeoJSON models
- Reused existing dataset contracts
- Added shared dataset table construction helper
- Enforced explicit schema and geometry requirements
- Added strict scalar serialization rules

### Notes

- No repository implementations added
- No CRUD logic added
- No schema inference introduced
- No geometry inference introduced
- No metadata or identifiers invented
- No business logic added
- Existing APIs remain unchanged
- Serialization operates exclusively through explicit dataset contracts

## [0.4.3] - 2026-07-22

### Changed

#### Sprint 4.4 – Dataset Contracts

- Introduced reusable `DatasetScalar` type alias
- Refactored `DatasetRow` to use `DatasetScalar`
- Reduced duplication in tabular dataset contracts
- Improved maintainability without changing behavior

### Notes

- No API changes
- No validation changes
- No serialization changes
- No exception changes
- Refactoring only

## [0.4.2] - 2026-07-22

### Added

#### Sprint 4.3 – File Repository Infrastructure

- Added shared file support utilities
- Added dataset file format detection
- Added immutable filesystem metadata model
- Added deterministic dataset discovery
- Added CSV validation infrastructure
- Added CSV record counting
- Added GeoJSON FeatureCollection validation infrastructure
- Added GeoJSON feature counting
- Reused existing GeoJSON parser for validation
- Added UTF-8/BOM-safe dataset loading
- Applied Rule of Two for shared filesystem abstractions

### Notes

- No repository implementations added
- No CRUD operations implemented
- No dataset identifiers introduced
- No metadata values fabricated
- No import/export functionality added
- No API endpoints changed
- File infrastructure currently provides reusable read-only utilities only

---

## [0.4.1] - 2026-07-22

### Added

#### Sprint 4.2 – Repository Contracts

- Added repository protocol architecture
- Added generic repository contracts
- Added `RepositoryProtocol`
- Added `ReadOnlyRepositoryProtocol`
- Added `WritableRepositoryProtocol`
- Applied Interface Segregation Principle (ISP)
- Adopted `typing.Protocol` for structural typing
- Added strongly typed generic repository interfaces
- Added reusable repository validation contract
- Added reusable repository metadata contract

### Notes

- No repository implementations added
- No filesystem access introduced
- No persistence logic added
- No business logic added
- No API endpoints changed
- Repository layer currently defines reusable contracts only

## [0.4.0] - 2026-07-22

### Added

#### Sprint 4.1 – Data Layer Foundation

- Added data-layer exception hierarchy
- Added immutable dataset metadata models
- Added dataset statistics model
- Added dataset bounds model
- Added dataset information model
- Added reusable dataset validation utilities
- Reused GIS BoundingBox and CRS contracts
- Added deterministic validation helpers
- Added metadata timestamp validation
- Added dataset path, version, source, and name validation

### Notes

- No repository implementation added
- No filesystem access introduced
- No persistence logic added
- No API endpoints changed
- Data layer currently defines reusable contracts only

---

## [0.3.0] - 2026-07-22

### Added

#### Sprint 3 – GIS Foundation

##### Sprint 3.1 – GIS Foundation

- GIS constants
- Coordinate Reference System (CRS) support
- GIS exception hierarchy
- GIS validation utilities

##### Sprint 3.2 – Geometry Models & Spatial Operations

- Point model
- BoundingBox model
- Distance calculations (Haversine)
- Initial bearing calculation
- Geometry helper utilities
- Spatial validation

##### Sprint 3.3 – GeoJSON Parsing & Serialization

- GeoJSON Point model
- GeoJSON Feature model
- GeoJSON FeatureCollection model
- Point serialization/deserialization
- Feature serialization/deserialization
- FeatureCollection serialization/deserialization
- GeoJSON validation
- JSON helper utilities

---

## [0.2.0] - 2026-07-21

### Added

#### Sprint 2 – Core Backend Components

- Shared API schemas
- Generic response models
- Domain models
- Validation utilities
- Common enums
- Health response schema
- Standardized error responses

#### Sprint 2.2 – Validation Exception Refinement

- Domain-specific validation exceptions
- Structured validation metadata
- Field-aware validation issues
- Request ID propagation
- Standardized validation error handling

---

## [0.1.0] - 2026-07-21

### Added

#### Sprint 1 – Backend Foundation

- FastAPI application factory
- Centralized configuration using pydantic-settings
- Environment variable support (.env)
- Structured logging configuration
- Request logging middleware
- Global exception handling
- Health check endpoint (/health)
- API router registration
- OpenAPI (Swagger & ReDoc) configuration
- Type-safe application settings
