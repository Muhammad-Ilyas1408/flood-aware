# Flood-Aware Spatial Evidence Engine

## Purpose

`backend.app.gis` is the Spatial Evidence Engine for the Flood-Aware AI-Powered Flood
Decision Support System. It produces deterministic, validated spatial facts that
downstream AI reasoning can consume. It supports DEM sampling, flood-zone buffering,
WorldPop exposure aggregation, OSM infrastructure extraction, and infrastructure
intersections. Its responsibility ends when those factual results are produced.

## AI-First Design Principle

This module exists solely to generate trustworthy spatial evidence for downstream AI
reasoning. It produces facts such as:

- Flood polygons and extent
- Population exposure
- Infrastructure impacts
- DEM elevation
- Spatial metadata and provenance

### This module MUST NOT

- Interpret flood risk
- Predict future flooding
- Generate recommendations
- Prioritise emergency response
- Perform reasoning
- Call LLMs
- Register runtime tools
- Become a generic GIS framework

### Before Adding New GIS Code

Every proposed GIS feature must answer: `Does this improve the quality, reliability,
performance, or completeness of AI evidence?` If the answer is no, defer it until
after the MVP.

## Dependency flow

```text
GIS configuration / types
    -> RasterCache and raster utilities
    -> DEMLoader / WorldPopLoader / OSMLoader
    -> FloodZoneGenerator / PopulationExposureCalculator / InfrastructureImpactCalculator
    -> FloodEvidenceBuilder
```

Only `FloodEvidenceBuilder` imports the immutable `ForecastResult` as factual input.
The GIS layer does not import Runtime, RAG, API, or Tool Registry code.

## Module responsibilities

- `config.py`: immutable CRS, raster, flood, infrastructure, and population settings.
- `types.py`: minimal shared GIS type aliases.
- `cache.py`: instance-owned, thread-safe LRU raster reader cache. Call `close()` at
  the composition boundary to release file handles.
- `raster.utilities`: metadata extraction and geometry clipping used by raster-backed
  exposure analysis.
- `evidence.py`: immutable composition of existing GIS and forecast facts for AI use.
- `processing`: application-facing GIS processing components.

## Extension points

- Pass one shared `RasterCache` to DEM and WorldPop loaders when their lifecycles are
  composed together.
- Replace only the `FloodZoneGenerator` implementation when approved hydraulic
  modelling becomes available; preserve its output contract.

## Future integration

`FloodEvidenceBuilder` combines existing forecast, flood-zone, population, infrastructure,
and optional elevation facts without performing new spatial calculations or risk reasoning.
Forecast severity remains an input and the GIS layer must not derive severity, register
runtime tools, or call AI systems.
