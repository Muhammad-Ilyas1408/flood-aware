# Flood-Aware Project Board

---

## Sprint 1 – Backend Foundation

Status: Completed
Completed: 2026-07-21

Deliverables:

- [x] FastAPI application
- [x] Configuration system
- [x] Logging
- [x] Middleware
- [x] Exception handlers
- [x] Health endpoint
- [x] Swagger documentation

---

## Sprint 2 – Core Backend Components

Status: Completed
Completed: 2026-07-21

Deliverables:

- [x] Shared API schemas
- [x] Domain models
- [x] Common response models
- [x] Validation utilities
- [x] Validation exception refinement

---

## Sprint 3 – GIS Foundation

Status: Completed
Completed: 2026-07-22

### Sprint 3.1 – GIS Foundation

- [x] GIS constants
- [x] CRS support
- [x] GIS exception hierarchy
- [x] GIS validation utilities

### Sprint 3.2 – Geometry Models & Spatial Operations

- [x] Point model
- [x] BoundingBox model
- [x] Distance calculations
- [x] Initial bearing
- [x] Geometry helper utilities
- [x] Spatial validation

### Sprint 3.3 – GeoJSON Parsing & Serialization

- [x] GeoJSON Point
- [x] GeoJSON Feature
- [x] GeoJSON FeatureCollection
- [x] Point serialization
- [x] JSON serialization/deserialization
- [x] GeoJSON validation

---

## Sprint 4 – Data Layer

Status: In Progress

---

### Sprint 4.1 – Data Layer Foundation

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] Data-layer exception hierarchy
- [x] Dataset metadata models
- [x] Dataset statistics model
- [x] Dataset bounds model
- [x] Dataset information model
- [x] Data validation utilities

---

### Sprint 4.2 – Repository Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] RepositoryProtocol
- [x] ReadOnlyRepositoryProtocol
- [x] WritableRepositoryProtocol
- [x] Generic repository typing
- [x] Repository metadata contract
- [x] Repository validation contract

---

### Sprint 4.3 – File Repository Infrastructure

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] File infrastructure
- [x] CSV validation
- [x] GeoJSON validation
- [x] Dataset discovery
- [x] Filesystem metadata extraction

---

### Sprint 4.4 – Dataset Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] DatasetColumnType
- [x] DatasetColumn
- [x] DatasetSchema
- [x] DatasetRow
- [x] DatasetTable
- [x] Dataset scalar type alias

---

### Sprint 4.5 – Serialization Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] CSV serialization
- [x] CSV deserialization
- [x] GeoJSON serialization
- [x] GeoJSON deserialization
- [x] Explicit schema validation
- [x] Explicit geometry validation
- [x] Reusable serialization utilities

---

### Sprint 4.6 – Repository Configuration Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] FileRepositoryConfig
- [x] Repository configuration validation
- [x] Path validation
- [x] Metadata validation
- [x] Schema validation
- [x] File format validation

---

### Sprint 4.7 – Repository Protocol Refinement

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] DatasetTableRepositoryProtocol
- [x] Protocol separation
- [x] Repository protocol refinement
- [x] Interface Segregation refinement
- [x] Dataset-oriented repository support

### Sprint 4.8 – Repository Implementations

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] CSVRepository
- [x] GeoJSONRepository
- [x] DatasetTableRepositoryProtocol implementation
- [x] Repository validation
- [x] Repository loading
- [x] FileRepositoryConfig integration
- [x] Explicit schema-based loading
- [x] Explicit metadata-based loading

---

## Sprint 5 - Services

Status: Completed
Completed: 2026-07-22

### Sprint 5.1 – Service Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] DatasetServiceProtocol
- [x] VillageServiceProtocol
- [x] ShelterServiceProtocol
- [x] Structural service contracts
- [x] Service layer architecture

---

### Sprint 5.2 – Service Implementations

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] DatasetService
- [x] VillageService
- [x] ShelterService
- [x] Repository composition
- [x] Constructor dependency injection
- [x] DatasetTableRepositoryProtocol integration

---

### Sprint 5.3 – Service Configuration / Dependency Wiring

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] Dependency factory functions
- [x] create_dataset_service()
- [x] create_village_service()
- [x] create_shelter_service()
- [x] Centralized repository construction
- [x] Explicit dependency injection
- [x] CSV repository wiring

---

### Sprint 5.4 – Service Tests

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] Repository integration tests
- [x] Service integration tests
- [x] Dependency factory tests
- [x] CSV repository validation tests
- [x] GeoJSON repository validation tests
- [x] Negative validation scenarios

---

## Sprint 6 – API Layer

Status: Completed
Completed: 2026-07-23

---

### Sprint 6.1 – API Contracts

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] VillageResponse
- [x] VillageListResponse
- [x] ShelterResponse
- [x] ShelterListResponse
- [x] DatasetSummaryResponse
- [x] Reused shared response wrappers
- [x] Reused DatasetMetadata
- [x] Reused DatasetStatistics
- [x] Standardized API response contracts

---

---

#### Sprint 6.1.1 – Clean Architecture Refinement

Status: Completed
Completed: 2026-07-22

Deliverables:

- [x] Introduced application DTO layer
- [x] Removed API schema dependency from services
- [x] Added immutable DTO contracts
- [x] Added DTO → API translation layer
- [x] Added DatasetCatalogDTO
- [x] Replaced positional catalog with explicit named datasets
- [x] Preserved dependency injection
- [x] Preserved repository architecture
- [x] Updated service tests
- [x] Restored Clean Architecture dependency direction

---

#### Sprint 6.1.6 – Application Composition Root

Status: Completed

Completed: 2026-07-23

Deliverables:

- [x] Composition Root
- [x] Runtime DatasetCatalogConfig ownership
- [x] configure_dataset_dependencies()
- [x] get_village_service()
- [x] get_shelter_service()
- [x] get_dataset_catalog_service()
- [x] Service protocol dependency providers
- [x] ApplicationConfigurationError
- [x] ApplicationError
- [x] Explicit runtime configuration
- [x] Clean Architecture dependency preservation

---

### Sprint 6.2 – API Endpoints

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] GET /villages
- [x] GET /shelters
- [x] GET /datasets/catalog
- [x] Service integration
- [x] FastAPI routers
- [x] OpenAPI documentation
- [x] Endpoint integration tests
- [x] Centralized exception handling

## Sprint 7 – Application Use Cases

Status: Completed
Completed: 2026-07-23

### Sprint 7.1 – Application Layer Foundation

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] Application Use Case layer
- [x] Application package structure
- [x] Clean orchestration boundary

---

### Sprint 7.2 – Use Case Protocols

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] ViewVillagesUseCaseProtocol
- [x] ViewSheltersUseCaseProtocol
- [x] ViewDatasetCatalogUseCaseProtocol

---

### Sprint 7.3 – Concrete Use Cases

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] ViewVillagesUseCase
- [x] ViewSheltersUseCase
- [x] ViewDatasetCatalogUseCase
- [x] DTO passthrough orchestration

---

### Sprint 7.4 – Composition Providers

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] get_village_use_case()
- [x] get_shelter_use_case()
- [x] get_dataset_catalog_use_case()
- [x] Composition Root integration

---

### Sprint 7.5 – API Migration

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] API depends on use-case protocols
- [x] Endpoint migration
- [x] DTO translation preserved

---

### Sprint 7.6 – Application Layer Tests

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] Use case delegation tests
- [x] DTO identity verification
- [x] Application Layer isolation tests

---

## Sprint 8 – AI Decision Layer

Status: Completed
Completed: 2026-07-23

---

### Sprint 8.1 – AI Layer Foundation

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] AI package
- [x] AI architecture boundary
- [x] Package organization

---

### Sprint 8.2 – AI Domain Models

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] DecisionRequest
- [x] DecisionContext
- [x] DecisionResult
- [x] Recommendation
- [x] RecommendationPriority
- [x] ToolResult

---

### Sprint 8.3 – AI Tool Protocols

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] VillageToolProtocol
- [x] ShelterToolProtocol
- [x] DatasetCatalogToolProtocol
- [x] Structural AI interfaces

---

### Sprint 8.4 – AI Tool Implementations

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] Village Tool
- [x] Shelter Tool
- [x] Dataset Catalog Tool
- [x] Immutable ToolResult generation

---

### Sprint 8.5 – Decision Engine

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] DecisionEngine
- [x] Deterministic orchestration
- [x] Immutable DecisionContext propagation
- [x] Request context preservation
- [x] Placeholder recommendation
- [x] ToolResult aggregation

---

### Sprint 8.6 – Decision Engine Tests

Status: Completed
Completed: 2026-07-23

Deliverables:

- [x] Contract tests
- [x] Tool invocation verification
- [x] Context propagation verification
- [x] ToolResult identity verification
- [x] Recommendation verification
- [x] Failure propagation verification
- [x] LangGraph-ready implementation-independent tests

---

## Sprint 9 – AI Runtime Infrastructure

Status: Completed
Completed: 2026-07-24


---

### Sprint 9.1 – Runtime Infrastructure

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] Runtime package organization
- [x] Tool Registry
- [x] Tool Metadata
- [x] Runtime Tool Executor
- [x] Runtime Exception Hierarchy
- [x] Runtime Lifecycle States
- [x] Decision Lifecycle States
- [x] Sequential Planner
- [x] Execution Memory
- [x] Execution Trace

---

#### Sprint 9.1.5 – Runtime Composition

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] AIRuntime composition facade
- [x] Planner composition
- [x] Executor composition
- [x] Registry composition
- [x] Execution Memory composition
- [x] Execution Trace composition
- [x] Stable runtime boundary

---

### Sprint 9.2 – Runtime Tool Integration

Status: Completed
Completed: 2026-07-24

---

#### Sprint 9.2.0 – Production Dataset Projection

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] Repository-boundary production dataset projection
- [x] Village dataset projection
- [x] Shelter dataset projection
- [x] Frozen DTO compatibility
- [x] Frozen service compatibility
- [x] Production dataset support
- [x] Repository projection tests

---

#### Sprint 9.2.1 – Runtime Integration Validation

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] End-to-end runtime validation
- [x] Village runtime execution
- [x] Shelter runtime execution
- [x] Dataset Catalog runtime execution
- [x] Runtime registration validation
- [x] Sequential runtime execution
- [x] DecisionContext preservation
- [x] Runtime failure validation
- [x] Production dataset integration

---

### Sprint 9.3 – Government Knowledge Engine (RAG Tool)

Status: Completed
Completed: 2026-07-24

---

#### Sprint 9.3.0 – Government Knowledge Base

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] Government document loader
- [x] PDF cleaning pipeline
- [x] Semantic chunking
- [x] OpenAI embedding service
- [x] Chroma persistent vector store
- [x] Government Retriever
- [x] Knowledge Tool
- [x] Prompt Builder
- [x] Response Generator
- [x] Immutable RAG models
- [x] Framework-independent protocols
- [x] Offline index builder

---

#### Sprint 9.3.1 – Government Knowledge Evaluation

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] Benchmark Loader
- [x] Evaluation Runner
- [x] Retrieval Metrics
- [x] Citation Checker
- [x] Metrics Aggregator
- [x] Evaluation Report Writer
- [x] Evaluation CLI
- [x] evaluation.json generation
- [x] evaluation.md generation
- [x] Evaluation tests

---

#### Sprint 9.3.2 – Benchmark Synchronization

Status: Completed
Completed: 2026-07-24

Deliverables:

- [x] Benchmark synchronization utility
- [x] Automatic chunk-id synchronization
- [x] Automatic citation synchronization
- [x] Preserve benchmark metadata
- [x] Documented synchronization workflow

---

### Sprint 9.4 – Weather Tool

Status: Completed
Completed: 2026-07-24

Completed

- [x] Weather package implemented
- [x] OpenWeatherMap client
- [x] Typed request/result models
- [x] Weather mapper
- [x] Exception hierarchy
- [x] Unit tests
- [x] Live verification script
- [x] Documentation completed

---

### Sprint 9.5 – GloFAS Forecast Tool

Status: Completed
Completed: 2026-07-25

---

#### Sprint 9.5.0 – Forecast Tool Foundation

Status: Completed
Completed: 2026-07-25

Deliverables:

- [x] Forecast package
- [x] Forecast domain models
- [x] Forecast settings
- [x] Forecast exception hierarchy
- [x] Forecast parser
- [x] Forecast mapper
- [x] Forecast tool
- [x] Snapshot locator
- [x] Forecast verification script

---

#### Sprint 9.5.1 – Forecast Ingestion

Status: Completed
Completed: 2026-07-25

Deliverables:

- [x] GloFAS ingestion service
- [x] CDS download client
- [x] Deterministic snapshot naming
- [x] Metadata persistence
- [x] Snapshot storage
- [x] Ingestion tests

---

#### Sprint 9.5.2 – Forecast Processing

Status: Completed
Completed: 2026-07-25

Deliverables:

- [x] NetCDF parsing
- [x] Coordinate extraction
- [x] Time decoding
- [x] Lead time decoding
- [x] Discharge extraction
- [x] Forecast mapping
- [x] Immutable ForecastResult
- [x] Forecast processing tests

---

#### Sprint 9.5.3 – Forecast Architecture Refinement

Status: Completed

Completed: 2026-07-25

Deliverables:

- [x] SnapshotLocator introduced
- [x] Filesystem traversal removed from Forecast Tool
- [x] Parser fail-fast metadata validation
- [x] Ingestion metadata annotation
- [x] Forecast Tool verification
- [x] Architecture refinement completed

---

### Sprint 9.6 – GIS Flood Analysis Tool

Status: Completed
Completed: 2026-07-26

---

#### Sprint 9.6.0 – GIS Foundation

Status: Completed
Completed: 2026-07-26

Deliverables:

- [x] GIS package
- [x] GIS configuration
- [x] GIS shared types
- [x] Raster cache
- [x] Raster utilities
- [x] GIS documentation

---

#### Sprint 9.6.1 – Terrain & Flood Processing

Status: Completed
Completed: 2026-07-26

Deliverables:

- [x] DEM loader
- [x] DEM metadata extraction
- [x] Elevation sampling
- [x] Flood Zone Generator
- [x] Deterministic flood buffering
- [x] Flood processing tests

---

#### Sprint 9.6.2 – Population & Infrastructure Processing

Status: Completed
Completed: 2026-07-26

Deliverables:

- [x] WorldPop loader
- [x] Population Exposure Calculator
- [x] OSM loader
- [x] Infrastructure Impact Calculator
- [x] Infrastructure processing tests

---

#### Sprint 9.6.3 – AI Spatial Evidence

Status: Completed
Completed: 2026-07-26

Deliverables:

- [x] Immutable FloodEvidence
- [x] FloodEvidenceBuilder
- [x] GIS evidence aggregation
- [x] Flood evidence tests
- [x] Architecture refinement completed

---

## Sprint 10 – LangGraph Decision Agent

Status: Completed
Completed: 2026-07-27

---

### Sprint 10.1 – Graph Definition

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] LangGraph foundation
- [x] Graph runtime
- [x] Graph builder
- [x] Immutable graph state
- [x] Dependency injection boundaries

---

### Sprint 10.2 – Evidence Infrastructure

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Weather Tool node
- [x] Forecast Tool node
- [x] GIS Tool node
- [x] Village Tool node
- [x] Shelter Tool node
- [x] Dataset Catalog node
- [x] Government Knowledge node

---

#### Sprint 10.2.4 – Architecture Cleanup

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Dependency cleanup
- [x] Graph composition cleanup
- [x] Node standardisation
- [x] Documentation updates

---

### Sprint 10.3 – Conditional Routing

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Forecast severity routing
- [x] Graph branching
- [x] Deterministic routing policies

---

### Sprint 10.4 – Evidence Aggregation

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Immutable evidence aggregation
- [x] Provenance tracking
- [x] Duplicate detection
- [x] Conflict detection
- [x] Execution trace integration

---

### Sprint 10.5 – LLM Decision Agent

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Decision contracts
- [x] Prompt builder
- [x] Response parser
- [x] Provider abstraction
- [x] OpenAI provider
- [x] Recommendation mapper

---

#### Sprint 10.5.1 – Architecture Refinement

Status: Completed
Completed: 2026-07-27

Deliverables:

- [x] Provider boundary cleanup
- [x] Prompt metadata
- [x] Naming improvements
- [x] Documentation improvements

---

#### Sprint 10.6 – Failure Recovery

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Timeout handling
- [x] Retry policy
- [x] Circuit breaker
- [x] Typed failures
- [x] Health monitoring
- [x] Deterministic fallback

---

### Sprint 10.7 – Observability & Production Hardening

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Correlation context
- [x] Structured logging
- [x] Timing utilities
- [x] Metrics abstraction
- [x] Version metadata
- [x] Provider health reporting
- [x] Production dataset bootstrap
- [x] Startup dataset initialization
- [x] Runtime validation
- [x] Swagger verification
- [x] OpenAPI verification

---

## Sprint 11 – LLM Reasoning & Grounded Recommendation

Status: Completed
Completed: 2026-07-28

---

### Sprint 11.1 – Grounded Prompt & Citation Enforcement

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] EvidenceReferenceIndex (closed citation vocabulary)
- [x] Rebuilt grounded, citation-aware, conflict-aware prompt instructions
- [x] DecisionGroundingError + parser-level grounding validation
- [x] Strict OpenAI structured-output schema transform
- [x] Grounding failures integrated into existing retry budget

---

### Sprint 11.2 – Golden-Set Evaluation

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] 12-scenario real-API golden-set suite
- [x] Production decision-provider composition factory
- [x] Shared reference-aggregation test helper
- [x] RUN_GOLDEN_SET-gated execution (no incidental API cost)
- [x] 12/12 scenarios passing, confirmed across repeated runs

---

### Sprint 11.3 – Fallback Regression & Housekeeping

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Persistent-failure retry-exhaustion regression test
- [x] RecommendationNode fallback-mapping regression test
- [x] evidence_nodes.py rename (was skeletons.py) — naming accuracy only, no behavior change
- [x] Full suite (225 tests) verified passing post-rename
- [x] Logging-discipline review (reasoning trace intentionally excluded from logs)
- [x] Manual qualitative review of real LLM output

---

## Sprint 12 – Reliable Multi-Tool Agent Behavior

Status: Completed
Completed: 2026-07-28

---

### Sprint 12.1 – Routing Audit & Baseline Verification

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Real-runtime routing test suite (5 query-intent scenarios)
- [x] docs/routing-decision-table.md
- [x] Verified: routing is severity-based, not query-intent-based
- [x] Query-intent selection explicitly scoped out, documented as future work

---

### Sprint 12.2 – Graceful Tool-Failure Degradation

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Shared `_record_tool_failure` helper
- [x] All 7 evidence nodes wrapped in failure-recovery path
- [x] FAILED vs. SKIPPED trace distinction at point of execution
- [x] Existing node-failure tests updated to assert recoverable-error behavior

---

### Sprint 12.3 – Precondition-Skip Handling

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Identity-based SKIPPED classification in GraphRuntime
- [x] Weather/Forecast/GIS/Knowledge nodes skip gracefully on missing precondition
- [x] Dormant-node COMPLETED mislabeling incidentally corrected
- [x] Coordinate-less end-to-end graph run verified (no crash)
- [x] Confirmed skip detection is identity-based, not value-equality-based

---

### Sprint 12.4 – Concurrency Verification

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Concurrent dual-request regression test
- [x] Verified no shared-state leakage across concurrent graph executions

---

## Sprint 13 – Multi-Turn Conversation & Follow-Up Questions

Status: Completed
Completed: 2026-07-28

---

### Sprint 13.1 – Conversation State Model

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] ConversationTurn / ConversationSession immutable models
- [x] Async-safe in-memory ConversationSessionStore

---

### Sprint 13.2 – Deterministic Evidence-Reuse Policy

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] requires_new_evidence() pure function
- [x] Unit tests: first turn, identical context, changed location, partial context

---

### Sprint 13.3 – Conversation-Aware Prompting

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] Backward-compatible `history` parameter on PromptBuilder.build()
- [x] History-scoped grounding instruction (no prior-evidence citation)

---

### Sprint 13.4 – Conversation Orchestration

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] ConversationOrchestrator
- [x] Fixed: redundant duplicate LLM call on fresh-evidence turns
- [x] Fixed: decision/ → conversation/ dependency-direction violation (ConversationTurnLike protocol)
- [x] Explicit DecisionGenerationError on graph fallback without canonical decision

---

### Sprint 13.5 – Multi-Turn Verification

Status: Completed
Completed: 2026-07-28

Deliverables:

- [x] 3 orchestration-level spy-based multi-turn tests
- [x] 3 real golden-set multi-turn tests (RUN_GOLDEN_SET=1)
- [x] Verified: evidence reuse, evidence refresh, no cross-turn leakage, real grounding, history ordering
- [x] Full suite (247 tests) passing

---

## Hotfix – Live Verification & Reasoning-Quality Hardening

Status: Completed
Completed: 2026-07-29

---

### Hotfix 1 – Dataset Catalog Provenance Crash

Status: Completed
Completed: 2026-07-29

Deliverables:

- [x] Fixed DatasetEvidenceMapper AttributeError (PDF-provenance vs. dataset-provenance mismatch)
- [x] Real DatasetMetadata-based citation format
- [x] Verified live in manual_chat.py

---

### Hotfix 2 – RAG Citation Corruption

Status: Completed
Completed: 2026-07-29

Deliverables:

- [x] Fixed SemanticChunker._is_heading() numeric-table misclassification
- [x] Chroma government-knowledge index rebuilt (4 docs, 1,384 chunks)
- [x] Verified clean citations live

---

### Hotfix 3 – Developer Tooling & Observability

Status: Completed
Completed: 2026-07-29

Deliverables:

- [x] scripts/manual_chat.py (real end-to-end interactive verification tool)
- [x] ExtraFieldsFormatter for structured log visibility
- [x] Fixed conversation/__init__.py export gap

---

### Feature – Reasoning Specificity

Status: Completed
Completed: 2026-07-29

Deliverables:

- [x] _key_figures() prompt surfacing + SPECIFICITY instruction with contrast example
- [x] DecisionSpecificityError + parser enforcement
- [x] Fixed: citation/figure-label collision
- [x] Retry-with-feedback resilience mechanism (generalizes beyond single hallucination patterns)
- [x] Fixed: over-broad enforcement (village population false-positive)
- [x] Full suite: 256 passed, 1 skipped
- [x] Full golden set: 16/16 passing
- [x] Live multi-turn manual verification, including real retry-recovery observed in production

---

## Sprint 14 – Production Backend, Dashboard & Visual Identity

Status: **Completed**
Completed: 2026-07-31

---

### Sprint 14.1 – Production Composition Root & Conversation API
Status: Completed | 2026-07-29

- [x] 14.1.1 — Singleton composition root, fail-fast startup validation, GIS loader reuse
- [x] 14.1.2 — POST /conversation endpoint; fixed strict-mode session_id defect (blocked every real client); 503 for AI failures; 404 for unknown sessions
- [x] 14.1.3 — FOCUS prompt instruction (initial version) + golden test; documented ratio-metric methodology finding
- [x] 14.1.4 — Real Weather (OpenWeatherMap) + real Forecast (GloFAS, read-only) wired; snapshot staleness detection (internal + user-facing); fixed ForecastNode never populating evidence.forecast
- [x] 14.1.5 — GIS eager-parse caching (2–4min → ~30s per request); root cause documented (no persistent OSM PBF spatial index)

---

### Sprint 14.2 – Streamlit Dashboard & Production Hardening
Status: Completed | 2026-07-30

- [x] 14.2.1 — Situation Analysis page: dataset catalog, filterable tables, honest bounding-box map
- [x] 14.2.2 — AI Assistant Chat page: real multi-turn UI, rotating progress messages, distinct 404/503/connection-failure handling
- [x] 14.2.2 fix — Real village/shelter coordinates surfaced end-to-end (removed manual lat/lon entry requirement)
- [x] 14.2.3 — Real Weather/Forecast/GIS caching hardening (see 14.1.4/14.1.5); RAG relevance-floor fix (score_threshold wired up, dedup improved); root cause of FOCUS instability found and fixed (current_request_text never reached decide())
- [x] 14.2.4 — Shelter-action grounding refinement: DecisionActionGroundingError + parser-level enforcement, refined through 3 rounds of empirical verification against real examples

---

### Sprint 14.3 – Visual Identity & Policy Advisor
Status: Completed | 2026-07-31

- [x] Real theme (.streamlit/config.toml): navy/amber, badge-color-safe
- [x] Shared header component + accessibility-hook-based active-page sidebar styling
- [x] Real product naming: Flood-Aware Agent / Situation Room / Home, distinct per-page icons
- [x] New Policy Advisor page (no location selector, routes to Knowledge/Dataset only)
- [x] Page-appropriate rotating progress messages
- [x] Fixed: chat input bottom-pinning
- [x] Fixed: message rendering-order inconsistency (single source of truth)
- [x] Fixed: risk badges hidden on Policy Advisor (display-only)
- [x] Fixed: village selector UX (real placeholder, conditional manual fields)
- [x] Fixed: shelter-specific-question 503 (root-caused via captured live log — DecisionSpecificityError, not the initially-suspected error type)
- [x] Fixed: generalized specificity exemption to cover present-but-off-topic evidence, not just entirely-absent
- [x] Corrected 2 over-strict golden-test assertions found during this work
- [x] Full suite: 275 passed, 2 skipped | Full golden set: 21/21 passing
- [x] Extensive live end-to-end re-verification after full process restart

---

## Hotfix 14.4 – Regional GIS Dataset Extraction

Status: **Completed**
Completed: 2026-08-01

Deliverables:
- [x] scripts/extract_regional_gis_data.py (pyosmium reference-complete spatial extract + rasterio raster clip, 0.2° buffered Swat region)
- [x] scripts/compare_regional_gis_accuracy.py (read-only validation tool)
- [x] Bit-for-bit accuracy confirmed: river geometry, population/infrastructure exposure, all 7 infrastructure categories — identical between original and regional files
- [x] graph_dependencies.py wired to regional extracts; manual_chat.py updated for consistency
- [x] File size reduction: OSM 147.2 MiB → 4.2 MiB (~97.1%); WorldPop 134.9 MiB → 2.0 MiB (~98.5%)
- [x] Real startup time: 5–6 min → 39 sec (~88–90% reduction)
- [x] Real production-path verification via live dashboard (GIS citations, real reasoning confirmed post-swap)
- [x] Original Pakistan-wide files preserved, untouched, still in repo

---

## Sprint 15 – Next.js Production Frontend

Status: **Completed**
Completed: 2026-08-01
Branch: frontend-nextjs, merged into dev and main (backend untouched except the additive CORS fix; dashboard/ retired in a follow-up commit)

---

### Sprint 15.1 – Scaffolding & Design System
Status: Completed
- [x] Next.js 16 + TypeScript + Tailwind v4 + shadcn/ui scaffolded
- [x] Real design system (navy/amber, derived from existing Streamlit brand)
- [x] Font pairing (Inter + Space Grotesk)
- [x] Foundational primitives (Card, Badge w/ risk variants, PageShell)
- [x] Typed API contracts + client mirroring real backend schemas
- [x] Fixed: Node.js install + PATH propagation, CSS comment bug

### Sprint 15.2 – Home Page
Status: Completed
- [x] Server-rendered hero with real live stats (150 villages, 51 shelters)
- [x] Three feature cards, accurate copy, real hover/focus states
- [x] Confirmed responsive to mobile

### Sprint 15.3 – Flood-Aware Agent
Status: Completed
- [x] Real village selector (real coordinates, no manual entry)
- [x] Real chat: history, rotating status, badges, actions, citations
- [x] Distinct 404/503/network error handling
- [x] Fixed: CORS middleware added to backend (real, additive backend change)
- [x] Real live verification: grounded answers, session persistence, evidence reuse speedup, honest absent-evidence behavior

### Sprint 15.4 – Policy Advisor
Status: Completed
- [x] Shared chat logic extracted (useConversation hook), Agent regression-verified post-refactor
- [x] No village selector; risk badges correctly suppressed
- [x] Real live verification: real NDMP citations, no badges

### Sprint 15.5 – Situation Room
Status: Completed
- [x] Dataset provenance cards, sortable/filterable tables
- [x] Real interactive map (react-leaflet, React 19-compatible) with real per-record markers — genuine improvement over Streamlit version
- [x] Real live verification: real counts, real markers, real sort/filter

### Sprint 15.6 – Navigation & Visual Polish
Status: Completed
- [x] Persistent site header, real navigation, accessible active-state, mobile menu
- [x] Home hero centering + staggered animation
- [x] Chat message entrance animation, staggered response reveal, status cross-fade
- [x] "Start new conversation" button polish, missing icon fix (Agent)
- [x] Missing-evidence UX: raw category names translated to plain-language sentences, muted supporting-context treatment (not hidden — deliberate honesty preserved)
- [x] Fixed: cramped chat area — 3-round root-cause investigation (padding double-subtraction → header border → real-world subpixel variance), each verified with progressively deeper evidence (DOM class list → compiled CSS → DevTools Computed styles)

---

**Sprint 15 fully complete.** All four pages built, verified live against the real backend, real navigation, real polish. Streamlit dashboard retained as working reference. Ready for deployment planning or further feature work.

## Sprint 16 – Production Deployment

Status: **Completed** (branch merge & Streamlit retirement deferred to next session)
Completed: 2026-08-02

---

### Sprint 16.1 – Backend Deployment (Railway)
Status: Completed
- [x] Full deployment audit (entrypoint, dependencies, env vars, runtime data requirements)
- [x] Platform pivot: Render (real card-required billing risk, confirmed via research) → Railway (genuinely no-card-required)
- [x] Committed required runtime data (GIS extracts, Chroma store, latest GloFAS snapshot) via verified gitignore negation
- [x] Fixed: missing libexpat1/libsqlite3-0/libcurl4 system libraries (railpack.json), root-caused via real GitHub issues + manylinux policy docs
- [x] Live verified: /health 200, ~2s real GIS warm-up on production hardware, full real /conversation pipeline working

### Sprint 16.2 – Frontend Deployment (Vercel)
Status: Completed
- [x] Fixed: branch tracking (Production Environment settings, not Git settings, in current Vercel UI)
- [x] Fixed: Root Directory (frontend)
- [x] Fixed: stale Output Directory setting from initial misconfigured build
- [x] Live verified: all 4 routes rendering with real backend data at flood-aware.vercel.app

### Sprint 16.3 – CORS Production Hardening
Status: Completed
- [x] cors_allow_origin_regex added (dynamic Vercel URL support)
- [x] Rejected first draft regex (too permissive), pinned to real account slug
- [x] Verified against Starlette's real .fullmatch behavior + 3 real URLs + 5 adversarial cases
- [x] Live verified: real cross-origin request succeeds, full 3-page production walkthrough passed

---

**Real, live URLs:**
Frontend: https://flood-aware.vercel.app
Backend: https://flood-aware-production.up.railway.app

---

## Hotfix 18 – Small-Talk Routing, Policy Advisor RAG Scoping, and Missing-Evidence Fix

Status: **Completed** (merge to dev/main pending)
Completed: 2026-08-26
Branch: feature/conversational-scoping

- [x] Shared small-talk detection (`is_small_talk` + mode-aware canned reply), invoked once from `ConversationOrchestrator` for both Flood-Aware Agent and Policy Advisor
- [x] Policy Advisor scoped to explicit `mode=policy_advisor`, RAG-only via `KnowledgeTool` — no more implicit inference from absent coordinates
- [x] New `ConversationOutcome`/`response_type` contract: small-talk and policy-answer turns no longer forced into the flood-risk `Decision` schema
- [x] Root-caused and fixed the "dataset, dataset, dataset..." `missing_evidence` bug via vocabulary validation + dedup in `DecisionParser`
- [x] Frontend: `mode` plumbing, response-type-aware rendering, 300ms pending-bubble delay to stop inaccurate status-message flashes
- [x] Backend: 287 passed, 2 skipped (full suite, excl. golden)
- [x] Golden set (real API, run by project owner): 20/21 first run; the 1 failure (`test_follow_up_narrows_focus_to_policy_not_general_overview`) reran 3/4 pass — known LLM response-order variance, grounding held in every run, not a regression
- [x] Frontend: `tsc` + ESLint clean

**Not yet done:** merge into dev/main.

**Completed in follow-up session:** frontend-nextjs merged into dev and main; dashboard/ (Streamlit) retired, having fully served its purpose as a reference implementation during development.