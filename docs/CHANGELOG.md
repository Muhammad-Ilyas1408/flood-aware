# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

---

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