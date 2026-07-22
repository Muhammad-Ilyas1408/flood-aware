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

### Sprint 6.1.1 – Clean Architecture Refinement

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

### Sprint 6.1.6 – Application Composition Root

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