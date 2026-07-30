# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

---

## [1.5.0] - 2026-07-30

---

## Sprint 14.2 – Streamlit Dashboard & Production Hardening (2026-07-30)

### Sprint 14.2.1 — Situation Analysis Page

#### Added

- Added `dashboard/` Streamlit application (`app.py`, `config.py`, `api_client.py`), a thin client calling only existing, tested FastAPI endpoints — no business logic duplicated in the frontend.
- Added `dashboard/pages/situation_analysis.py`: dataset catalog summary, filterable village/shelter tables, and a dataset-level bounding-box map with an explicit, honest notice when per-record coordinates are unavailable rather than fabricating positions.
- Added `streamlit`, `streamlit-folium`, `folium` as real dependencies (versions confirmed against PyPI, not assumed).

### Sprint 14.2.2 — AI Assistant Chat Page

#### Added

- Added `dashboard/pages/ai_assistant_chat.py`: real multi-turn chat UI wired to `POST /conversation`, using `st.chat_message`/`st.chat_input`, session-state-persisted conversation history, colored risk/confidence badges, prioritized action lists, and a collapsible citations panel.
- Added rotating, honestly-worded progress messages during the real multi-second/minute wait (a background thread performs the blocking API call; only the main thread touches Streamlit UI elements, per Streamlit's threading constraints) — a deliberate choice over fabricating fake granular progress, since true per-node streaming isn't available from the backend.
- Added distinct, user-facing handling for all three real failure modes: session-not-found (404, auto-starts a new conversation), recommendation-service-unavailable (503, no silent auto-retry), and generic connection failure — each with its own honest message, verified live against real triggered failures.

#### Fixed

- **Manual coordinate entry removed entirely.** `GET /villages`/`GET /shelters` previously discarded real latitude/longitude columns that already existed in the source CSVs, at a hardcoded 3-column projection layer (`config/datasets.py`, `data/repositories.py`) — this silently forced every chat request through either a village with no real location data (causing GIS/Forecast to be honestly but confusingly skipped for every village) or manual lat/lon entry no real user should need. Extended the schema/DTO/API chain (`DatasetColumnType`, `VillageDTO`/`ShelterDTO`, `VillageResponse`/`ShelterResponse`) to surface real coordinates end-to-end; the chat page now auto-derives coordinates from the selected village with zero manual entry required.

---

### Sprint 14.2.3 — Real-Traffic Production Fixes

Found and fixed via live dashboard testing — not surfaced by any automated test suite, since the mocked fixtures used throughout the day's automated tests didn't reproduce these specific real-data conditions.

#### Fixed

- **GIS re-parsing on every fresh-evidence request.** GDAL's OSM vector driver has no persistent spatial index for `.osm.pbf` files — a `bbox=` filter narrows results, not scan cost, which is dominated by total file size. Added `warm_up()` to `RiverNetworkLoader`/`OSMLoader`, eagerly parsing the full Pakistan-wide dataset once at application startup and serving all subsequent requests from the in-memory result via spatial clipping. Real measured fresh-evidence request time reduced from 2–4 minutes to ~30 seconds after the one-time startup cost.
- **Real Weather (OpenWeatherMap) and Forecast (GloFAS) wired into production**, replacing the deterministic stand-ins used since Sprint 14.1. Forecast reads only the newest already-ingested local snapshot; live GloFAS/CDS ingestion is confirmed unsuitable for a synchronous request path (the `cdsapi` client has an unbounded blocking poll loop) and remains a deliberately separate, independently-run process. Added snapshot staleness detection (`ForecastEvidence.snapshot_age_hours`/`snapshot_stale`, configurable threshold, default 48h), surfaced both internally (confidence reasoning) and to the end user via the existing `missing_evidence` mechanism — a deliberate design choice, since hiding data-freshness caveats from users is the wrong default for a disaster-response tool.
- **RAG retrieval had no relevance floor.** `ChromaVectorStore.search()`'s existing `score_threshold` parameter was never actually passed by either of its two callers, so retrieval always returned Chroma's raw top-5 nearest neighbors unconditionally — including weak/boilerplate matches (a repeated PDF title/preamble page was cited as "government policy" guidance in live testing). Wired a real, empirically-derived threshold (confirmed Chroma's squared-L2 distance metric and OpenAI embedding normalization before deriving the number, rather than guessing) through `KnowledgeTool`/`GovernmentRetriever`/`ChromaVectorStore`; zero-results-above-threshold now returns an honest "no sufficiently relevant guidance found" result without calling the LLM. Extended `ContextBuilder` deduplication to catch near-duplicate boilerplate text across different chunk IDs, not just exact chunk-ID matches.
- **Root-caused today's FOCUS instability.** `ConversationOrchestrator`/`RecommendationNode` never passed the current turn's raw request text into `decide()` — only the evidence bundle and prior-turn history. The FOCUS prompt instruction (added earlier this session) was asking the model to "address what the CURRENT request specifically asks about" while the current request's text was never actually present anywhere in the prompt. This was a structural data-flow gap, not a prompt-wording problem, and explains the instability across multiple same-day wording attempts. Added a `current_request_text` parameter (backward-compatible) threaded through `decide()`/`PromptBuilder.build()`/both real call sites; live re-verification confirmed a real "what about shelters" follow-up now correctly leads with named, specific shelter details instead of a generic recap.

### Verified

- Full suite: 274 passed, 2 skipped.
- Full golden set: 18/18 passing (including new multi-turn shelter-focus and policy-focus scenarios).
- Extensive live, real-API, real-UI verification across multiple villages and multi-turn conversations, including a real observed 503 (recommendation service temporarily unavailable) with correct user-facing handling and successful recovery on resend.

### Notes — known issue, actively investigating

- Live testing surfaced one further real inconsistency, found in this session's final verification pass: a real "what about shelters?" follow-up produced a response summary stating "no specific shelter data is available" while simultaneously showing real citations and giving specific shelter-preparedness actions in the same response. Not yet root-caused — diagnostic investigation (raw `Decision` object plus the turn's stored `EvidenceBundle.shelters` field, via the real `ConversationOrchestrator` rather than a lower-level probe) is queued as the first task of the next session, to determine whether this is a text-generation inconsistency or a genuine evidence gap specific to certain requests.
- Real Weather/Forecast integration deliberately excludes automated ingestion scheduling; refreshing the local GloFAS snapshot before a demo remains a manual/scheduled step, explicitly deferred as future work.
- Policy/knowledge-focused chat page (skipping location selection for pure policy questions) identified as a good, small future UX improvement — not undertaken this session.
- Sprint 14.2.3 completed; one open issue carried forward.
- Ready for Sprint 14.2.4 (shelter-inconsistency fix) → Sprint 14.3 (visual polish pass).

---

### Notes — known issue, actively investigating (revised)

- Live dashboard testing surfaced an apparent inconsistency (a response
  claiming "no shelter data available" while showing real citations and
  specific shelter advice). A same-day diagnostic using the real
  ConversationOrchestrator (not a lower-level probe) did NOT reproduce
  that specific inconsistency — instead it surfaced a more fundamental,
  separate finding: real shelter evidence collection (`EvidenceBundle.
  shelters`) returned genuinely empty for Mingora in that diagnostic run,
  despite Mingora having confirmed real shelter records in `shelters.csv`
  and returning real shelter data reliably in numerous earlier tests this
  same session. When evidence is genuinely empty, the model's response
  was actually internally consistent (correctly citing only dataset-level
  provenance, correctly flagging the gap in `missing_evidence`) — so this
  is likely evidence of intermittent shelter-collection failure, not a
  reasoning/grounding bug. The original live dashboard symptom and this
  new empty-evidence finding may be two faces of the same underlying
  flakiness. Root-causing why shelter collection intermittently returns
  empty for a village with confirmed real data — including checking
  whether Sprint 12's `_record_tool_failure` degradation path logged a
  real exception during collection, which would distinguish a silently
  swallowed error from a genuine empty-but-successful lookup — is queued
  as the first task of the next session.

---

### Notes — investigation closed

- The apparent "shelter data inconsistency" observed in live dashboard
  testing was fully investigated and root-caused: village and shelter
  evidence collection are correctly, symmetrically gated by
  route_after_gis (Sprint 12) to only run at MAJOR/EXTREME severity —
  confirmed via direct reproduction that both fields come back equally
  empty at MODERATE severity, with no silent failure, matching-logic
  asymmetry, or caching issue involved. This is working as designed, not
  a bug.
- One legitimate, undecided product question remains: at severities below
  MAJOR/EXTREME, the model currently still generates a generic
  shelter-preparedness action even when it explicitly states shelter data
  is unavailable — non-hallucinated but arguably over-specific for
  entirely-absent evidence. Queued as a scoped decision for the Sprint
  14.3 polish pass: either accept generic-but-honest action wording as-is,
  or tighten the prompt so entirely-absent categories are only mentioned
  in missing_evidence, never turned into a specific action.

---

## [1.4.0] - 2026-07-29

---

## Sprint 14.1 – Production Composition Root & Conversation API (2026-07-29)

### Sprint 14.1.1 — Production Graph Composition Root

#### Added

- Added `backend/app/config/graph_dependencies.py`: `configure_graph_dependencies()`, constructing the full real tool stack (village/shelter/dataset services and tools, GIS river/OSM/WorldPop loaders + `GISDomainService`, government knowledge tool, real `build_openai_decision_provider()`) exactly once at FastAPI application startup, mirroring `scripts/manual_chat.py`'s composition but as a true singleton stored on `application.state` rather than rebuilt per invocation.
- Added `get_conversation_orchestrator(request)`, a request-scoped dependency provider matching the existing `get_village_service(request)` pattern.
- Added `close_graph_dependencies()`, releasing vector store/river/WorldPop loader resources at application shutdown.
- Wired both into `main.py`'s existing lifespan sequence, idempotently guarded.
- Weather and Forecast use the same deterministic static stand-ins as `manual_chat.py` (explicit, deliberate v1.0 scope decision — real API/GloFAS integration deferred as separate follow-up work).

#### Verified

- GIS river-network loading confirmed already internally cached (`RiverNetworkLoader`); `OSMLoader` has no internal cache but is now constructed once at startup regardless, eliminating per-request re-parsing structurally via the composition root rather than requiring a second caching layer.
- Fails fast with a clear `ApplicationConfigurationError` if required GIS data files or `OPENAI_API_KEY` are missing at startup, rather than accepting traffic and failing on first request.

---

### Sprint 14.1.2 — POST /conversation Endpoint

#### Added

- Added `backend/app/schemas/conversation.py`: `ConversationRequest`/`ConversationResponse`, exposing only client-appropriate fields (risk level, confidence, summary, actions, citations, missing_evidence) — internal fields (full evidence bundle, reasons, conversation history) explicitly excluded from the response surface, verified by dedicated test assertions.
- Added `backend/app/api/conversation.py`: `POST /conversation`, registered in the existing router aggregation, following the established villages/shelters router conventions exactly.
- Added `backend/tests/test_conversation_api.py`: integration tests using `app.dependency_overrides`, no real OpenAI/GIS calls.

#### Fixed

- **Request-schema strict-mode defect:** `ConversationRequest` originally inherited `strict=True`, which rejects `session_id: UUID` unless the caller supplies an already-constructed Python `UUID` object — impossible for any real JSON client, since JSON has no native UUID type. This made the documented "supply a session_id to continue a conversation" contract unsatisfiable for every real caller. Removed `strict=True` from the inbound request schema (response schemas remain strict, since they are always constructed internally from typed domain objects, never parsed from external input). Audited all other request fields; confirmed none share this defect.
- **Unhandled `DecisionGenerationError` mapped to 503:** added `handle_decision_generation_error`, returning a clean, generic "temporarily unavailable" message with safe server-side logging (exception type only, never message/internals), registered ahead of the catch-all handler.
- **Unhandled unknown-session `ValueError` mapped to 404:** added `backend/app/conversation/exceptions.py` (`ConversationError`/`ConversationSessionNotFoundError`, following the existing `decision/exceptions.py` domain-hierarchy convention) and `handle_conversation_session_not_found_error`, returning a safe "session not found, start a new conversation" message. Test explicitly asserts neither the raw session UUID nor the exception class name appear in the response body.

#### Verified

- Full test suite: 260 passed, 1 skipped.
- Live end-to-end verification against a real running server (`uvicorn`): real multi-turn conversation via `POST /conversation` with real GIS/village/shelter/knowledge tools and real OpenAI reasoning; observed the Sprint 13 retry-with-feedback mechanism recover live from a real grounding correction; confirmed evidence reuse (no GIS re-parse) on same-context follow-up; confirmed real 404 for an unknown session ID and real 503-shaped handling wired correctly.

---

### Sprint 14.1.3 — Multi-Turn Reasoning Focus

#### Added

- Added a FOCUS instruction to `PromptBuilder._SYSTEM_INSTRUCTIONS`' conversation-history paragraph, with a weak/strong contrast example built from real captured production output: follow-up questions must primarily address what the current request specifically asks, using prior turns for continuity only rather than re-deriving a general overview each turn.
- Added `test_follow_up_narrows_focus_to_shelters_not_general_overview` (`backend/tests/golden/test_conversation_golden_set.py`), a real multi-turn golden-set scenario proving the fix against the live API.

#### Notes — measurement methodology finding

- Initial test design measured focus via a shelter-action ratio threshold; this proved unreliable not because the prompt fix was ineffective, but because the underlying metric (a ratio over typically 2–3 discrete actions) cannot support a stable threshold comparison — real API variance moved the ratio between 0.33/0.5/0.67 across identical repeated calls, with no threshold value avoiding false failures. Replaced with a coarser, structural pass/fail check instead: at least one action must be shelter-grounded, and the first (highest-priority) action specifically must be shelter-grounded — proving shelters lead the response rather than measuring an inherently noisy proportion. Verified stable across 3 consecutive real-API runs plus the full 17-test golden set.

### Notes

- No changes to `decision/parser.py`, `evidence_reference_index.py`, or `models.py`.
- Real Weather (OpenWeatherMap) and real Forecast (GloFAS) integration explicitly deferred — static stand-ins remain in production composition root pending scoped follow-up work.

---

## Sprint 14.1.4 – Real Weather & Forecast Integration (2026-07-29)

### Added

- Wired real `WeatherTool` (OpenWeatherMap, synchronous per-request) into the production composition root, replacing `_StaticWeatherTool`. Fails fast at startup via `ApplicationConfigurationError` if `OPENWEATHER_API_KEY` is missing.
- Wired real `GloFASForecastTool` into the production composition root, replacing `_StaticForecastProvider`. Reads only the newest already-ingested local snapshot from `data/glofas/`; deliberately never triggers live GloFAS/CDS ingestion from the request path (confirmed via investigation: the underlying `cdsapi` client has an unbounded blocking poll loop unsuitable for a synchronous request handler). Ingestion remains an explicitly separate, independently-run process (`scripts/ingest_glofas_snapshot.py`).
- Added snapshot staleness detection: `ForecastEvidence` gained `snapshot_age_hours`/`snapshot_stale` fields, computed in `ForecastNode` from the snapshot file's modification time against a configurable threshold (`GLOFAS_MAX_SNAPSHOT_AGE_HOURS`, default 48h — one full tolerated missed/delayed GloFAS daily publication cycle).
- Staleness is surfaced **both internally and to the end user**, via the existing `missing_evidence` mechanism rather than a new field: a stale forecast produces a human-readable notice (e.g. "forecast (data is approximately 4 days old)") that reaches `Recommendation.missing_evidence` and the real API response, and separately causes the model's confidence reasoning to treat a stale forecast as non-authoritative (extending the existing SINGLE-SOURCE CONFIDENCE instruction).
- Removed both static stand-in classes (`_StaticWeatherTool`, `_StaticForecastProvider`) entirely — no dead code left behind.

### Fixed

- **`ForecastNode` never populated `evidence.forecast`:** discovered during investigation — the node only ever wrote to `state.forecast_result` (the raw domain object), leaving `state.forecast` (the `ForecastEvidence` the prompt actually reads) permanently at its empty default. This meant every prior conversation session reported "forecast" as entirely absent in `missing_evidence`, even when real discharge data existed in `forecast_result`. Fixed as part of this work (required for staleness to be representable at all); existing test assertion in `test_forecast_node.py` updated to reflect the corrected, intentional behavior.

### Verified

- Full test suite: 267 passed, 1 skipped.
- Full golden set (17 real-API scenarios): 17/17 passing.
- Live end-to-end verification against a real running server across two real villages (Mingora — major severity, triggers full tool suite; Barikot — normal severity, minimal tool suite):
  - Real weather/forecast values genuinely differ per location and differ from the old fixed stand-in values.
  - Staleness notice correctly and consistently surfaced across multiple real turns.
  - System correctly and honestly declined to fabricate shelter guidance when real shelter evidence was genuinely absent (Barikot, normal severity — GIS/Village/Shelter never triggered by existing severity-based routing).
  - System correctly produced a shelter-led, FOCUS-compliant follow-up response when real shelter evidence was genuinely present (Mingora, moderate/major severity).

### Notes — real finding, deferred as future work

- Live testing surfaced a legitimate design gap, not a bug: because tool routing is purely severity-based (Sprint 12), a user's explicit question (e.g. "what about shelters?") cannot itself trigger GIS/Village/Shelter evidence collection if computed severity alone wouldn't have triggered it. This is the same query-intent-based-routing gap Sprint 12 already identified and explicitly deferred — now with a concrete real-world example. Recommended as a scoped future enhancement (e.g. "intent-aware supplementary tool invocation"), not undertaken in this session.
- Live-observed inconsistency, not yet root-caused: one real response (Barikot follow-up) included `"shelters"` in `missing_evidence` as a bare word, differing in form from the forecast staleness notice's descriptive phrasing — worth a closer look in a future session, low priority given it doesn't affect grounding correctness.
- No changes to `decision/parser.py`, `evidence_reference_index.py`, or `models.py`'s core `Decision` contracts.
- GloFAS ingestion scheduling (periodic automated refresh) remains a separate, explicitly deferred follow-up task.
- Sprint 14.1 (composition root, conversation API, real Weather/Forecast wiring) is now fully complete.

---

## Sprint 14.1.5 – GIS Loader Eager-Parse Caching (2026-07-29)

### Added

- Added `warm_up()` to `RiverNetworkLoader` and `OSMLoader`, eagerly parsing the full-extent Pakistan-wide OSM PBF dataset exactly once, ahead of any request.
- Both loaders now retain the parsed full-extent layer(s) in memory (`_full_extent_layer`/`_full_extent_layers`) and serve every subsequent request by spatially clipping (`geometry.intersects(box(*bbox))`) the already-in-memory result, instead of re-reading from disk per request.
- `configure_graph_dependencies()` now calls `warm_up()` on both loaders once at application startup.
- `OSMLoader` gained a `close()` method (previously held no closable state) for symmetric shutdown cleanup alongside `RiverNetworkLoader`.

### Fixed

- **Root cause identified and resolved:** GDAL's OSM vector driver has no persistent spatial index for `.osm.pbf` files — a `bbox=` filter on `gpd.read_file()` narrows returned *results*, not the underlying *scan cost*, which is dominated by total file size, not query area. This meant every fresh-evidence conversation turn re-parsed the entire Pakistan-wide dataset from scratch (measured: 28–92s for river network, 65–220s for OSM infrastructure), regardless of the small region actually queried. Real per-request GIS collection time reduced from ~90 seconds–4 minutes to ~30 seconds (dominated by the remaining, unavoidable LLM reasoning and other tool calls), by moving the expensive parse to a one-time application-startup cost instead.

### Verified

- Full test suite passing, including two new tests per loader: `parses_disk_once_across_multiple_distinct_bboxes` (proves distinct bounding boxes are served from one in-memory parse, using a self-enforcing `side_effect` pattern that raises `StopIteration` on any unintended second disk read) and `warm_up_parses_the_dataset_once_before_any_request`.
- Live end-to-end verification: a real fresh-evidence conversation turn against a warmed-up server completed in 30.4 seconds (previously 2–4 minutes), with GIS evidence (`citations: gis`) confirmed intact and correct.

### Notes

- Tradeoff, accepted deliberately: application startup time grows by the one-time full parse cost (~90s–5min), paid once at process start rather than repeated per request. Both full-Pakistan geometries remain resident in memory for the application's lifetime. This matches the project's actual usage pattern (server started once, then serves many live requests).
- Regional PBF extraction (pre-clipping the source file to a Swat-district-only dataset via `osmium`/`ogr2ogr`) identified as the most durable long-term fix, explicitly deferred as a separate future data-preparation task — not a code change, out of scope for this session.
- Sprint 14.1 (composition root, conversation API, real Weather/Forecast, GIS caching) is now fully complete.
- Ready for Sprint 14.2 – Streamlit Dashboard.

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
