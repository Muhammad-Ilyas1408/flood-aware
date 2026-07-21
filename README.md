# Flood-Aware

> **An AI-Powered Flood Decision Support System for the Swat River Basin**
>
> Built using **LangGraph**, **RAG**, **GIS Analysis**, and **Large Language Models (LLMs)** to support flood risk assessment, population exposure analysis, and intelligent decision-making.

---

## Overview

Flood-Aware is an AI-assisted Decision Support System (DSS) that combines geospatial analysis, flood forecasting, Retrieval-Augmented Generation (RAG), and an AI decision agent to help both disaster management authorities and local communities understand flood risks and make informed decisions.

Instead of providing generic AI responses, the system grounds every recommendation using real flood forecasts, GIS datasets, and official disaster management knowledge.

---

# System Architecture

> **Architecture Diagram**
>
> *(This diagram will be added after the architecture implementation.)*

```text
                   Flood-Aware

         AI Flood Decision Support System

                    Dashboard
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
        ▼                ▼                 ▼

 Situation        AI Assistant      Scenario Simulator
  Analysis            Chat              What-if Analysis

        │                │                 │
        └────────────────┼─────────────────┘
                         │
                  LangGraph Decision Agent
                         │
      ┌──────────────────┼────────────────────┐
      │                  │                    │
 Forecast Tool      GIS Analysis Tool     RAG Knowledge Tool
      │                  │                    │
      └──────────────────┼────────────────────┘
                         │
                  Grounded Recommendation
```

---

# Features

### Flood Situation Analysis

- Analyze flood forecasts
- Estimate flood severity
- Identify affected regions

### GIS Spatial Analysis

- Population exposure estimation
- Flood zone visualization
- Administrative boundary analysis
- Infrastructure impact assessment

### AI Decision Support

- LangGraph Decision Agent
- Multi-tool reasoning
- Context-aware recommendations
- Explainable AI responses

### Retrieval-Augmented Generation (RAG)

- Query official disaster management documents
- Ground AI responses using trusted knowledge
- Citation-aware recommendations

### Interactive AI Assistant

- Natural language interface
- English support
- Urdu support
- Follow-up questions

### Scenario Simulation

Evaluate hypothetical flood situations such as:

- Heavy rainfall
- Dam overflow
- River water level increase
- Different forecast scenarios

---

# Technology Stack

## Backend

- Python
- FastAPI
- Pydantic

## AI & LLM

- LangGraph
- LangChain
- OpenAI API / Gemini API
- FAISS / ChromaDB

## GIS & Spatial Analysis

- GeoPandas
- Rasterio
- Shapely
- PyProj
- OSM Data
- WorldPop
- Copernicus DEM

## Dashboard

- Streamlit

## Data Sources

- GloFAS Flood Forecast
- WorldPop
- Copernicus DEM
- OpenStreetMap
- PDMA / NDMA Documentation

---

# System Workflow

```text
User Request
      │
      ▼
Dashboard
      │
      ▼
LangGraph Decision Agent
      │
      ├──────── Forecast Tool
      │
      ├──────── GIS Analysis Tool
      │
      ├──────── RAG Knowledge Tool
      │
      ▼
Evidence Aggregation
      │
      ▼
LLM Reasoning
      │
      ▼
Grounded Recommendation
      │
      ▼
Dashboard Response
```

---

# Project Structure

```text
Flood-Aware/
│
├── backend/
│   └── app/
│       ├── agents/
│       ├── api/
│       ├── config/
│       ├── core/
│       ├── gis/
│       ├── graph/
│       ├── models/
│       ├── prompts/
│       ├── rag/
│       ├── schemas/
│       ├── services/
│       ├── tools/
│       └── utils/
│
├── dashboard/
├── data/
├── docs/
├── experiments/
├── scripts/
├── tests/
│
├── README.md
├── LICENSE
└── pyproject.toml
```

---

# Development Roadmap

## Phase 1

- Repository Setup
- Project Documentation
- Configuration Management

## Phase 2

- FastAPI Backend
- LangGraph Workflow
- Dashboard UI

## Phase 3

- GIS Engine
- Population Exposure Analysis
- Flood Forecast Integration

## Phase 4

- RAG Pipeline
- AI Decision Agent
- Interactive Chat

## Phase 5

- Scenario Simulator
- Evaluation
- Testing
- Final Deployment

---

# Current Status

Current Stage:

**Project Planning & Architecture**

Upcoming Milestone:

- Dependency Specification
- Backend Infrastructure
- FastAPI Setup

---

# Documentation

Project documentation is available inside the `docs/` directory.

- Software Requirements Specification (SRS)
- Technical Design Specification (TDS)
- Architecture
- API Documentation
- Development Plan
- Data Inventory
- Changelog

---

# License

This project is licensed under the MIT License.

See the **LICENSE** file for details.