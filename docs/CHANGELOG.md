# Changelog

All notable changes to this project will be documented in this file.

---

## [Unreleased]

---

## [0.1.0] - 2026-07-21

### Added
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

### Sprint 1 – Backend Foundation
Completed:
- FastAPI project structure
- Configuration system
- Logging
- Middleware
- Exception handling
- Health endpoint
- API documentation

### Sprint 2 – Core Backend Components
Completed:
- Shared API schemas
- Generic response models
- Domain models
- Validation utilities
- Common enums
- Health response schema
- Standardized error responses

### Sprint 2.2 – Validation Exception Refinement
Completed:
- Domain-specific validation exceptions
- Structured validation metadata
- Field-aware validation issues
- Request ID propagation
- Standardized validation error handling

### Sprint 3.1 – GIS Foundation
Completed:
- GIS constants
- Coordinate Reference System (CRS) support
- GIS exception hierarchy
- GIS validation utilities

### Sprint 3.2 – Geometry Models & Spatial Operations
Completed:
- Immutable Point model
- Immutable BoundingBox model
- DistanceResult model
- Haversine distance calculations
- Initial bearing calculations
- Bounding box operations
- Geometry helper utilities
- Coordinate normalization
- Coordinate rounding

### Sprint 3.3 – GeoJSON Parsing & Serialization
Completed:
- GeoJSON Point model
- GeoJSON Feature model
- GeoJSON FeatureCollection model
- Point ↔ GeoJSON conversion
- GeoJSON serialization/deserialization
- GeoJSON validation
- Point-only GeoJSON support