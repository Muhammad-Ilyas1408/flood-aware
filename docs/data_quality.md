# Data Quality Report

## Flood-Aware Project

**Version:** 2.0
**Last Updated:** August 2026

---

# Purpose

This document describes the quality, provenance, limitations, and intended use of the datasets used by the Flood-Aware system.

The project relies on two primary real-world datasets:

* Village Dataset
* Shelter Dataset

These datasets serve as the foundational evidence source for the application's runtime tools and AI decision-support reasoning. For the complete technical inventory of all datasets (including GIS extracts, GloFAS snapshots, and the government knowledge base), see `docs/DATA_INVENTORY.md`. This document focuses specifically on the quality and limitations of the village/shelter data.

---

# Dataset Overview

| Dataset  | Records | Primary Purpose                                       |
| -------- | ------: | ----------------------------------------------------- |
| Villages |     150 | Flood risk analysis and village information           |
| Shelters |      51 | Emergency shelter information and evacuation planning |

---

# Village Dataset

## Description

The Village Dataset contains information about villages located within the Swat district study area. It directly supports the deployed system's flood risk assessment, GIS population exposure analysis, and the decision agent's evidence-grounded reasoning.

---

## Fields

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

Note: the deployed REST API (`GET /villages`) exposes a narrower projection of these fields for client consumption. See `docs/API_DOCUMENTATION.md` for the exact public schema.

---

## Record Count

Total Records: **150**

---

## Missing Values

| Field      | Missing Records |
| ---------- | --------------: |
| Population |              62 |

Missing Population Percentage: **41%**

---

## Data Sources

Compiled from multiple publicly available sources including government census publications, public administrative information, district-level resources, community information websites, and open geographic information. Each record includes its original source whenever available.

---

## Verification Status

Village records contain an explicit verification status (Verified / Partially Verified / Unverified), which should always be considered alongside a system-generated recommendation.

---

## Known Limitations

* Population data is incomplete for a portion of villages.
* Some records originate from publicly available community sources rather than official administrative records.
* Population values may not reflect the most recent census.
* Infrastructure information may change over time.
* Geographic coordinates are approximate for some locations.
* Flood risk categories are simplified for the current project scope.

The system's grounding and honesty guarantees (see `README.md` — "Why This Is Different From a Generic AI Chatbot") are the primary mechanism for handling these limitations responsibly: when population or other village-level data is unavailable for a given request, the system explicitly discloses this rather than silently proceeding as if the data were complete.

---

# Shelter Dataset

## Description

The Shelter Dataset contains information about real emergency shelters relevant to flood events in the Swat district, supporting shelter lookup, evacuation planning, and the decision agent's shelter-related reasoning.

---

## Fields

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

Note: the deployed REST API (`GET /shelters`) exposes a narrower projection of these fields. See `docs/API_DOCUMENTATION.md` for the exact public schema.

---

## Record Count

Total Records: **51**

---

## Missing Values

| Field                  | Missing Records |
| ---------------------- | --------------: |
| Generator Availability |               2 |
| Medical Support        |               2 |

Missing values represent unavailable information rather than negative values.

---

## Data Sources

Collected from publicly available sources including government educational institution listings, public university information, district administration resources, publicly accessible institutional websites, and open geographic information.

---

## Verification Status

Shelter records contain an explicit verification status (Verified / Partially Verified / Unverified).

---

## Known Limitations

* Shelter capacities are approximate.
* Operational status may change over time.
* Infrastructure facilities may be updated without notice.
* Contact information may become outdated.
* Some facility information is unavailable.

Consistent with the Village Dataset, the deployed system discloses when shelter data is unavailable for a given request rather than fabricating shelter names, capacities, or status — this behavior is enforced at the response-parsing level, not left to the model's discretion (see `docs/CHANGELOG.md`, Sprint 14.2.4, for the specific engineering work behind this guarantee).

---

# Data Quality Principles

## Transparency
Missing information is preserved wherever possible. The project does not generate synthetic values to replace unavailable information.

## Explainability
Every record preserves its original source where available. The deployed system can always trace a claim back to its real evidence — including explicitly stating when no relevant record exists.

## Traceability
Datasets retain verification status, source information, and update timestamps where available, enabling auditing and validation.

## Reproducibility
The datasets can be recreated from their documented public sources; no proprietary or restricted datasets are required.

---

# Intended Usage

The datasets support a complete, deployed decision-support system for the Swat district. As with any dataset compiled substantially from publicly available sources rather than a single authoritative government feed, users — particularly disaster-management authorities relying on this system operationally — should be aware of the documented verification-status and completeness limitations above, and treat outputs as decision *support*, not a sole source of truth for emergency operations.

---

# Future Improvements

Potential future enhancements include integrating additional trusted external services such as:

* Overpass API for richer OSM-derived infrastructure detail
* Government GIS datasets with higher-resolution administrative boundaries
* Pakistan Meteorological Department data as a secondary weather source
* Real-time shelter availability/occupancy updates
* Dynamic evacuation routing

---

# AI Considerations

The system's decision agent, RAG knowledge tool, weather tool, and forecast tool are all explicitly designed around the documented limitations of these datasets: when requested information is unavailable, the system communicates that limitation directly to the user rather than generating unsupported or fabricated information. This is not an aspirational design goal — it is enforced by real, tested validation logic, documented in full in `docs/CHANGELOG.md`.

---

# Summary

The current datasets provide a real, deployed foundation for the Flood-Aware system's runtime tools and AI decision-support architecture. Some fields contain missing or approximate information, consistent with their compilation from publicly available sources rather than a single authoritative feed — the system prioritizes transparency, explainability, and honest disclosure of these gaps over presenting a false impression of completeness.