# Software Requirements Specification (SRS)

**Project:** Flood-Aware — Grounded Flood Decision Support System
**BS Computer Science Final Year Project**
Department of Computer Science, University of Peshawar (Session 2022–2026)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for Flood-Aware, a decision-support system that provides evidence-grounded flood risk assessments and recommendations for the Swat River Basin, Khyber Pakhtunkhwa. It is intended for use by disaster-management authorities, local officials, and community members seeking reliable, non-fabricated guidance during flood events.

### 1.2 Scope

Flood-Aware combines real-time weather data, hydrological forecasting, geospatial exposure analysis, and official government disaster-management documentation into a single, conversational decision-support interface. The system is explicitly designed to avoid a known failure mode of generic LLM-based tools: producing confident-sounding but fabricated answers when the underlying evidence is missing or incomplete.

The system consists of:
- A FastAPI backend orchestrating a LangGraph-based multi-tool decision agent
- A production Next.js web frontend
- A Streamlit reference dashboard (used during development, retained as a secondary interface)

Out of scope for the current version: real-time push notifications/alerts, multi-language support beyond English, coverage areas outside the configured Swat district region, and automated emergency-service dispatch integration.

### 1.3 Intended Audience

Disaster-management officials (PDMA/NDMA-affiliated), local government authorities, and community members in the Swat district. Secondary audience: academic examiners evaluating this project as a Final Year Project submission.

### 1.4 Definitions and Abbreviations

| Term | Definition |
|---|---|
| DSS | Decision Support System |
| GIS | Geographic Information System |
| RAG | Retrieval-Augmented Generation |
| LLM | Large Language Model |
| GloFAS | Global Flood Awareness System (Copernicus hydrological forecast) |
| PDMA | Provincial Disaster Management Authority |
| NDMP | National Disaster Management Plan |
| Grounding | The requirement that every AI-generated claim be traceable to real, cited evidence |
| Evidence Bundle | The aggregated real-time and reference data (weather, forecast, GIS, village/shelter, government documents) supplied to the decision agent for a given request |

---

## 2. Overall Description

### 2.1 Product Perspective

Flood-Aware is a new, standalone system. It integrates with several external data sources (OpenWeatherMap, the Copernicus Climate Data Store/GloFAS, OpenStreetMap, WorldPop) but does not depend on or extend any pre-existing internal system.

### 2.2 Product Functions (Summary)

1. Assess current flood risk for a specified village, combining real-time weather, hydrological forecast, and GIS-derived exposure data
2. Answer follow-up questions within a persistent, multi-turn conversation, reusing already-collected evidence where appropriate
3. Answer government policy and disaster-management guidance questions, grounded in official PDMA/NDMP documents
4. Display real village, shelter, and dataset information, including an interactive map
5. Explicitly and honestly disclose when relevant evidence is missing, stale, or unavailable, rather than fabricating a response

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Expertise |
|---|---|---|
| Disaster-management official | Uses the system to assess risk and plan response, may ask detailed policy/procedural questions | Low to moderate |
| Community member | Uses the system to understand local flood risk and shelter availability | Low |
| Developer/maintainer | Extends or maintains the system | High |

### 2.4 Operating Environment

- Backend: Python 3.11+, deployed on Railway (Linux container, native Python runtime)
- Frontend: Next.js 16, deployed on Vercel
- Client: any modern web browser, desktop or mobile
- No client-side installation required

### 2.5 Design and Implementation Constraints

- The decision agent's output must be schema-validated structured JSON, not free-form text, to allow deterministic downstream grounding checks
- All AI-generated citations must be verifiable against a closed, per-request vocabulary of real evidence references — free-form or invented citations are rejected at the parser level, with the model given a corrective retry
- Live GloFAS forecast ingestion must never be triggered synchronously within a user-facing request (the underlying CDS API has an unbounded blocking queue); forecast data is read from a periodically-refreshed local snapshot
- The system must operate within free-tier hosting resource constraints (memory, cold-start time)

---

## 3. Functional Requirements

### FR-1 — Flood Risk Assessment
The system shall accept a natural-language flood-risk query for a specified village (selected from a real, known dataset) and return a structured assessment including a risk level (normal/moderate/high/extreme), a confidence level, a plain-language rationale, and a prioritized list of recommended actions.

### FR-2 — Evidence Grounding
Every claim, citation, and recommended action in a response shall be traceable to a specific, real item in that request's evidence bundle. The system shall reject and regenerate any response containing a citation not present in the allowed evidence vocabulary.

### FR-3 — Honest Evidence-Gap Disclosure
When a relevant evidence category (forecast, GIS, weather, village, shelter, or government knowledge) is entirely absent or has not been collected for a given request, the system shall explicitly disclose this in the response's `missing_evidence` field, translated into plain language for the end user, rather than omitting the gap or fabricating a substitute.

### FR-4 — Non-Fabrication of Specific Claims on Absent Evidence
The system shall not generate a recommended action containing invented specifics (names, capacities, numeric figures, definitive status claims) for any evidence category that is entirely absent from the request's evidence bundle. General, honest guidance (e.g., "obtain this information before finalizing plans") remains permitted.

### FR-5 — Multi-Turn Conversation
The system shall support follow-up questions within a persistent conversation session, identified by a session ID. When a follow-up does not require new location context, the system shall reuse previously collected evidence rather than re-fetching it. Follow-up responses shall substantively address the specific topic of the current question rather than repeating a prior turn's general overview.

### FR-6 — Government Policy Guidance
The system shall answer questions about government flood policy and disaster-management plans, retrieving and citing relevant passages from official PDMA/NDMP source documents. Retrieval results below a minimum relevance threshold shall be discarded rather than cited.

### FR-7 — Forecast Staleness Disclosure
When the most recently available hydrological forecast snapshot exceeds a configured age threshold, the system shall disclose this to the user and treat the forecast as non-authoritative in its confidence reasoning, rather than presenting outdated data as current.

### FR-8 — Real-Time Weather Integration
The system shall retrieve current weather conditions for the requested location from a live external weather service on each request.

### FR-9 — GIS Exposure Analysis
For requests classified at or above a moderate flood severity, the system shall compute real population and infrastructure exposure within a flood-affected buffer zone, derived from real geospatial datasets (OpenStreetMap, WorldPop).

### FR-10 — Village and Shelter Data Access
The system shall provide access to real, current village and shelter records (name, district, population/capacity, and geographic coordinates) via both a browsable interface and as evidence within the decision agent's reasoning.

### FR-11 — Situation Overview
The system shall provide a summary view of the datasets it operates on, including record counts, provenance, and an interactive map showing real village and shelter locations.

### FR-12 — Error Handling
The system shall distinguish, and present distinctly to the user, at minimum: an expired/unknown conversation session, a temporarily unavailable recommendation service, and a general connectivity failure — never exposing internal error details or stack traces to the end user.

---

## 4. Non-Functional Requirements

### NFR-1 — Grounding Integrity (Safety-Critical)
The system shall never present a fabricated claim as fact. This requirement takes precedence over response completeness or user experience smoothness.

### NFR-2 — Response Latency
A conversation turn reusing existing evidence within a session shall typically complete in under 10 seconds. A fresh-evidence turn (new location, first turn in a session) shall typically complete within 30–60 seconds under normal operating conditions.

### NFR-3 — Availability
The backend shall fail fast with a clear configuration error at startup if required credentials or data files are missing, rather than accepting traffic in a broken state.

### NFR-4 — Security
No API credentials or secrets shall be present in source code or version control. Cross-origin access to the backend API shall be restricted to explicitly known frontend origins.

### NFR-5 — Maintainability
The codebase shall follow a layered architecture (API → use cases → services → repositories) with dependency injection, enabling isolated unit testing without live external service calls.

### NFR-6 — Testability
Core grounding, specificity, and honesty logic shall be covered by both deterministic unit tests and a real-API "golden set" evaluation suite exercising the live LLM provider.

### NFR-7 — Deployability
The system shall be deployable on free-tier cloud hosting infrastructure, with a cold-start time suitable for interactive use (target: under one minute for GIS-dependent request paths).

---

## 5. External Interface Requirements

### 5.1 User Interfaces
- Web-based, responsive interface (Next.js), accessible via standard browsers on desktop and mobile
- Conversational chat interface for flood-risk and policy queries
- Tabular and map-based data browsing interface

### 5.2 API Interfaces
RESTful HTTP API (FastAPI), documented endpoints including `POST /conversation`, `GET /villages`, `GET /shelters`, `GET /datasets/catalog`, `GET /health`. Full schema detail in `docs/API_DOCUMENTATION.md`.

### 5.3 External System Interfaces
- OpenWeatherMap API (live weather data)
- Copernicus Climate Data Store / GloFAS (hydrological forecast snapshots, ingested offline)
- OpenStreetMap (regional extract, geospatial infrastructure data)
- WorldPop (population raster data)
- OpenAI API (structured decision reasoning, text embeddings)

---

## 6. Appendix

Full sprint-by-sprint development history, including specific bugs identified through live testing and their resolutions, is maintained in `docs/CHANGELOG.md`. Software architecture detail is maintained in `docs/architecture/LANGGRAPH_ARCHITECTURE.md` and `docs/architecture/LANGGRAPH_IMPLEMENTATION_CONTRACTS.md`.