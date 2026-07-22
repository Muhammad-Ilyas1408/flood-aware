# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

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