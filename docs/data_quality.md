# Data Quality Report

## Flood-Aware Project

**Version:** 1.0
**Last Updated:** 2026-07-24

---

# Purpose

This document describes the quality, provenance, limitations, and intended use of the datasets used by the Flood-Aware system.

The project currently relies on two primary datasets:

* Village Dataset
* Shelter Dataset

These datasets serve as the foundational knowledge source for the application's runtime tools and future AI decision-support capabilities.

---

# Dataset Overview

| Dataset  | Records | Primary Purpose                                       |
| -------- | ------: | ----------------------------------------------------- |
| Villages |     150 | Flood risk analysis and village information           |
| Shelters |      50 | Emergency shelter information and evacuation planning |

---

# Village Dataset

## Description

The Village Dataset contains information about villages located within the project study area.

The data is intended to support:

* Flood risk assessment
* Emergency response planning
* Village information retrieval
* Shelter recommendation
* Future AI reasoning

---

## Fields

The dataset currently contains the following information:

* Village ID
* Village Name
* District
* Tehsil
* Latitude
* Longitude
* Population
* Population Year
* Distance from River
* Road Access
* Health Facility Availability
* School Availability
* Nearest Shelter
* Flood Risk
* Verification Status
* Data Source

---

## Record Count

Total Records:

**150**

---

## Missing Values

| Field      | Missing Records |
| ---------- | --------------: |
| Population |              62 |

Missing Population Percentage:

**41%**

---

## Data Sources

The Village Dataset was compiled from multiple publicly available sources including:

* Government census publications
* Public administrative information
* District-level resources
* Community information websites
* Open geographic information

Each record includes its original source whenever available.

---

## Verification Status

Village records contain an explicit verification status.

Typical values include:

* Verified
* Partially Verified
* Unverified

The verification status should always be considered when making operational decisions.

---

## Known Limitations

The Village Dataset has the following limitations:

* Population data is incomplete for a portion of villages.
* Some records originate from publicly available community sources.
* Population values may not reflect the latest census.
* Infrastructure information may change over time.
* Geographic coordinates are approximate for some locations.
* Flood risk categories are simplified for the current project.

These limitations are acceptable for educational, research, and prototype AI decision-support purposes.

---

# Shelter Dataset

## Description

The Shelter Dataset contains information about potential emergency shelters available during flood events.

The dataset supports:

* Shelter lookup
* Evacuation planning
* Capacity estimation
* AI recommendations
* Future routing decisions

---

## Fields

The dataset currently contains:

* Shelter ID
* Shelter Name
* District
* Tehsil
* Latitude
* Longitude
* Capacity
* Building Type
* Generator Availability
* Water Availability
* Medical Support
* Female Facilities
* Wheelchair Accessibility
* Road Access
* Contact Number
* Operational Status
* Verification Status
* Last Updated
* Data Source

---

## Record Count

Total Records:

**50**

---

## Missing Values

| Field                  | Missing Records |
| ---------------------- | --------------: |
| Generator Availability |               2 |
| Medical Support        |               2 |

Missing values represent unavailable information rather than negative values.

---

## Data Sources

Shelter information was collected from publicly available sources including:

* Government educational institution listings
* Public university information
* District administration resources
* Publicly accessible institutional websites
* Open geographic information

Every shelter record includes a documented data source whenever possible.

---

## Verification Status

Shelter records contain an explicit verification status.

Typical values include:

* Verified
* Partially Verified
* Unverified

---

## Known Limitations

Current shelter information has several limitations:

* Shelter capacities are approximate.
* Operational status may change over time.
* Infrastructure facilities may be updated without notice.
* Contact information may become outdated.
* Some facility information is unavailable.

---

# Data Quality Principles

The Flood-Aware project follows the following principles regarding data quality.

## Transparency

Missing information is preserved whenever possible.

The project does **not** generate synthetic values to replace unavailable information.

---

## Explainability

Every record attempts to preserve its original source.

The AI system should always be able to explain where information originated.

---

## Traceability

Whenever available, datasets retain:

* Verification status
* Source information
* Update timestamps

This enables future auditing and validation.

---

## Reproducibility

The datasets can be recreated from their documented public sources.

No proprietary or restricted datasets are required.

---

# Intended Usage

The datasets are designed for:

* Educational purposes
* Research
* AI experimentation
* Flood decision-support prototypes
* Emergency planning demonstrations

They are **not** intended for real-world emergency operations without additional validation from official government agencies.

---

# Future Improvements

Future versions of the project may enhance these datasets by integrating trusted external services such as:

* OpenStreetMap
* Overpass API
* OpenRouteService
* Government GIS datasets
* Pakistan Meteorological Department data
* Provincial Disaster Management Authority (PDMA) data

Potential enhancements include:

* Nearest hospital distance
* Nearest school distance
* Road travel time
* Live weather information
* Flood alerts
* Real-time shelter availability
* Dynamic evacuation routing

---

# AI Considerations

Future AI components, including:

* Runtime Tools
* RAG Knowledge Tool
* Weather Tool
* Routing Tool
* Decision Agent

should consider the documented limitations of these datasets when generating recommendations.

If requested information is unavailable, the AI system should communicate that limitation explicitly rather than generating unsupported or fabricated information.

---

# Summary

The current datasets provide a practical and sufficiently detailed foundation for the Flood-Aware project's runtime tools and AI decision-support architecture.

Although some fields contain missing or approximate information, the datasets prioritize transparency, explainability, and traceability over completeness. This approach supports responsible AI development while providing a solid basis for future enrichment through trusted geospatial and governmental data sources.