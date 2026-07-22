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