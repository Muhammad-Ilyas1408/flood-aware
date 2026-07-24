# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

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