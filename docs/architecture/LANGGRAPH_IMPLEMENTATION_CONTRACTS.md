# 1. Foundation

---

# 1.1 Purpose

This document defines the **implementation-level contracts** for the LangGraph runtime used by the Flood-Aware AI Decision Support System.

Unlike `LANGGRAPH_ARCHITECTURE.md`, which describes the architectural vision and high-level system design, this document specifies the exact contracts required for implementation.

The objective is to remove implementation ambiguity so that every engineer, reviewer, and AI-assisted coding tool can implement the runtime consistently without introducing architectural assumptions.

This document is considered the authoritative implementation reference for:

- Sprint 10 – LangGraph Decision Agent
- Sprint 11 – LLM Reasoning
- Sprint 12 – AI Assistant
- Sprint 13 – Scenario Simulator
- Sprint 14 – Dashboard Integration
- Sprint 16 – System Evaluation
- Sprint 18 – Production Deployment

---

# 1.2 Scope

This specification defines the implementation contracts for:

- Graph Runtime
- Graph State
- Node Contracts
- Evidence Contracts
- Execution Trace
- Runtime Interfaces
- Tool Invocation
- Error Handling
- Compatibility Rules
- Validation Rules
- Ownership Rules
- Extension Points

This document intentionally does **not** describe:

- Flood prediction algorithms
- GIS processing algorithms
- Weather modelling
- Forecast generation
- RAG indexing
- UI implementation
- Infrastructure deployment

Those are specified elsewhere.

---

# 1.3 Relationship with Architecture Document

The Flood-Aware documentation hierarchy is intentionally layered.

```
LANGGRAPH_ARCHITECTURE.md
        │
        ▼
LANGGRAPH_IMPLEMENTATION_CONTRACTS.md
        │
        ▼
Production Source Code
```

Responsibilities of each document:

### LANGGRAPH_ARCHITECTURE.md

Defines:

- overall architecture
- design philosophy
- system decomposition
- routing philosophy
- planner strategy
- future compatibility

It answers:

> "How is the system designed?"

---

### LANGGRAPH_IMPLEMENTATION_CONTRACTS.md

Defines:

- exact models
- protocols
- interfaces
- runtime contracts
- immutable state
- compatibility rules
- implementation guarantees

It answers:

> "Exactly how must the system be implemented?"

---

### Source Code

Implements both documents.

The source code shall never contradict either specification.

---

# 1.4 Audience

This specification is intended for:

- Backend Engineers
- AI Engineers
- Software Architects
- Technical Reviewers
- QA Engineers
- Contributors
- AI Coding Assistants (e.g., Codex)

Every implementation of the LangGraph runtime shall conform to this document.

---

# 1.5 Normative Language

The following terminology is used throughout this specification.

| Word | Meaning |
|-------|----------|
| MUST | Mandatory requirement |
| MUST NOT | Absolutely prohibited |
| SHALL | Mandatory architectural rule |
| SHALL NOT | Forbidden architecture |
| SHOULD | Strong recommendation |
| SHOULD NOT | Discouraged unless justified |
| MAY | Optional |
| OPTIONAL | Implementation choice |

These terms follow the intent of RFC 2119 and RFC 8174.

---

# 1.6 Design Objectives

The implementation shall satisfy the following objectives.

## Determinism

Identical inputs must produce identical outputs unless explicitly configured otherwise.

---

## Immutability

Runtime state shall never be mutated in place.

Every node produces a new immutable GraphState.

---

## Explainability

Every recommendation shall be traceable to:

- executed nodes
- collected evidence
- retrieved documents
- tool outputs

---

## Grounded Decision Making

Recommendations shall only be derived from verified evidence.

The runtime shall never fabricate information.

---

## Replaceability

Every runtime component shall be replaceable without affecting unrelated components.

Examples:

- Planner
- LLM Provider
- Weather Provider
- GIS Engine
- Vector Store

---

## Testability

Every node shall be independently testable.

Every runtime component shall support deterministic unit testing.

---

## Extensibility

Future nodes shall integrate without modifying existing node contracts.

---

## Backward Compatibility

The LangGraph runtime shall preserve compatibility with the existing AI Runtime interfaces until migration is complete.

---

# 1.7 Architectural Principles

The following implementation principles govern the runtime.

---

## Principle 1 — Single Responsibility

Every runtime component owns exactly one responsibility.

Examples:

Weather Node

↓

Weather evidence only

NOT:

Forecast

GIS

Recommendation

---

## Principle 2 — Explicit Data Flow

Nodes communicate only through GraphState.

No hidden communication channels are permitted.

---

## Principle 3 — Immutable State

GraphState is append-only.

Nodes shall never modify existing objects.

---

## Principle 4 — Evidence Before Reasoning

Evidence collection always precedes reasoning.

The Recommendation Node is the only component permitted to perform AI reasoning.

---

## Principle 5 — Runtime Isolation

Node failures shall not terminate graph execution unless explicitly configured as fatal.

---

## Principle 6 — Interface First

All components interact through defined protocols.

Concrete implementations shall never be tightly coupled.

---

## Principle 7 — AI-First Design

The GIS subsystem exists solely to generate structured evidence for AI reasoning.

It shall not evolve into a generic GIS framework.

Every GIS capability must support one or more AI decision-making use cases.

---

# 1.8 Implementation Philosophy

The LangGraph runtime is designed as an orchestration layer rather than a business-logic layer.

Business logic remains inside individual tools.

The graph is responsible only for:

- orchestration
- routing
- state propagation
- evidence aggregation
- execution tracing
- recommendation generation

The graph shall never duplicate logic already implemented within tools.

---

# 1.9 Source of Truth

The implementation hierarchy shall be interpreted in the following order:

1. LANGGRAPH_IMPLEMENTATION_CONTRACTS.md
2. LANGGRAPH_ARCHITECTURE.md
3. Source Code
4. Unit Tests
5. Developer Documentation

If conflicts exist:

The higher-priority document prevails.

---

# 1.10 Change Management

All modifications to implementation contracts require:

- architectural review
- compatibility review
- documentation update
- regression testing

Changes shall not be introduced solely through source code.

Every implementation change affecting runtime behaviour must first be reflected in this specification.

---

# 1.11 Versioning

This specification follows semantic versioning.

Major version

Breaking implementation contracts

Minor version

New contracts or compatible extensions

Patch version

Editorial corrections and clarifications

---

# 1.12 Foundation Summary

This document serves as the definitive implementation specification for the Flood-Aware LangGraph runtime.

It establishes the contractual rules that every implementation must follow, ensuring consistency, determinism, explainability, extensibility, and long-term maintainability across Sprints 10 through 18.

Subsequent sections define the concrete models, protocols, runtime interfaces, and validation rules that transform the architectural design into production-ready implementation.

---

# 2. Common Types

## 2.1 Purpose

This section defines the foundational types used throughout the Flood-Aware LangGraph runtime.

These types are intentionally lightweight, immutable, and framework-independent wherever possible. They establish a common vocabulary shared by:

- Graph State
- Graph Nodes
- Runtime
- AI Tools
- Evidence Aggregation
- Execution Trace
- Recommendation Engine
- API Layer

Every implementation introduced in Sprint 10 and later MUST use these types unless explicitly documented otherwise.

---

# 2.2 Design Principles

The common type system follows the project's core engineering principles.

1. Strong typing.
2. Immutable data.
3. Deterministic behaviour.
4. Explicit ownership.
5. Serializable state.
6. Framework independence.
7. Forward compatibility.

No implementation may introduce anonymous dictionaries where an approved type exists.

---

# 2.3 Primitive Aliases

The following aliases improve readability throughout the implementation.

| Alias | Underlying Type | Description |
|---------|----------------|-------------|
| RequestID | UUID | Unique request identifier |
| ExecutionID | UUID | Runtime execution identifier |
| SessionID | UUID | Chat session identifier |
| NodeID | str | Unique graph node identifier |
| ToolName | str | Registered tool name |
| EvidenceID | UUID | Evidence identifier |
| CitationID | UUID | Citation identifier |
| Timestamp | datetime | UTC timestamp |
| Duration | float | Seconds |
| Confidence | float | Range 0.0–1.0 |

---

# 2.4 RuntimeMode

The runtime operates in one of the following modes.

```python
class RuntimeMode(str, Enum):
    LIVE = "live"
    SCENARIO = "scenario"
```

### LIVE

Uses live data sources.

Examples:

- ECMWF
- GloFAS
- Government knowledge
- OSM
- WorldPop

### SCENARIO

Uses synthetic inputs.

Examples:

- hypothetical rainfall
- dam overflow
- river rise
- simulated forecasts

---

# 2.5 GraphStatus

Represents overall graph execution status.

```python
class GraphStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"
    CANCELLED = "cancelled"
```

---

# 2.6 NodeStatus

Represents execution status of a single node.

```python
class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
```

---

# 2.7 EvidenceSeverity

Evidence severity expresses the seriousness of a single observation.

```python
class EvidenceSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
```

---

# 2.8 RecommendationPriority

Represents urgency of the final recommendation.

```python
class RecommendationPriority(str, Enum):
    INFORMATION = "information"
    WATCH = "watch"
    WARNING = "warning"
    EMERGENCY = "emergency"
```

---

# 2.9 ErrorSeverity

Errors are classified according to recoverability.

```python
class ErrorSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

---

# 2.10 ToolCategory

Every registered tool belongs to one category.

```python
class ToolCategory(str, Enum):
    WEATHER = "weather"
    FORECAST = "forecast"
    GIS = "gis"
    RAG = "rag"
    DATASET = "dataset"
    VILLAGE = "village"
    SHELTER = "shelter"
```

---

# 2.11 Coordinate

Represents a geographic point.

```python
class Coordinate(BaseModel):
    latitude: float
    longitude: float

    model_config = ConfigDict(frozen=True)
```

Constraints:

- Latitude:
    -90 ≤ latitude ≤ 90

- Longitude:
    -180 ≤ longitude ≤ 180

---

# 2.12 BoundingBox

Represents a rectangular geographic extent.

```python
class BoundingBox(BaseModel):
    west: float
    south: float
    east: float
    north: float

    model_config = ConfigDict(frozen=True)
```

Bounding boxes MUST use WGS84 coordinates.

---

# 2.13 TimeWindow

Represents a bounded temporal interval.

```python
class TimeWindow(BaseModel):
    start: datetime
    end: datetime

    model_config = ConfigDict(frozen=True)
```

Validation rules:

- start < end
- UTC only

---

# 2.14 Confidence Rules

Confidence values SHALL satisfy:

```
0.0 ≤ confidence ≤ 1.0
```

Interpretation:

| Range | Meaning |
|--------|----------|
| 0.00–0.20 | Very Low |
| 0.21–0.40 | Low |
| 0.41–0.60 | Moderate |
| 0.61–0.80 | High |
| 0.81–1.00 | Very High |

---

# 2.15 Immutability Requirement

All common types SHALL be immutable.

Implementation:

```python
model_config = ConfigDict(frozen=True)
```

No common type may expose mutable state.

---

# 2.16 Serialization

Every common type SHALL support:

- JSON serialization
- FastAPI serialization
- LangGraph state persistence
- deterministic hashing where applicable

No custom serialization logic should be required.

---

# 2.17 Versioning

Changes to common types are considered architecture-level changes.

Any modification SHALL:

- update this specification
- update CHANGELOG
- preserve backward compatibility whenever possible

---

# 2.18 Summary

The Common Types defined in this section establish the shared language used throughout the Flood-Aware platform.

Every subsequent implementation—including Graph State, Graph Nodes, Evidence Aggregation, Runtime orchestration, and AI reasoning—depends upon these immutable, deterministic, and strongly typed foundations.

No implementation may redefine these concepts outside this specification.

---

# 3. Canonical Models

---

## 3.1 Purpose

This section defines the canonical runtime models used by the Flood-Aware Decision Intelligence Platform.

These models represent the authoritative data contracts exchanged between:

- LangGraph runtime
- AI Runtime
- Tool nodes
- Evidence Aggregator
- Recommendation Engine
- FastAPI
- Streamlit Dashboard
- AI Assistant
- Scenario Simulator

These contracts are implementation-independent and SHALL remain stable across future releases.

All implementations MUST conform exactly to these models.

---

# 3.2 Design Principles

Every canonical model SHALL satisfy the following principles.

1. Immutable after creation.

2. Serializable.

3. Deterministic.

4. Thread-safe.

5. JSON compatible.

6. Version tolerant.

7. No hidden state.

8. No mutable collections.

9. No business logic.

10. Represent data only.

---

# 3.3 Model Ownership

Each model has exactly one owner.

| Model | Owner |
|---------|------|
| RuntimeContext | Runtime |
| UserRequest | Runtime |
| WeatherEvidence | Weather Tool |
| ForecastEvidence | Forecast Tool |
| GISEvidence | GIS Tool |
| VillageEvidence | Village Tool |
| ShelterEvidence | Shelter Tool |
| KnowledgeEvidence | Government Knowledge Tool |
| DatasetEvidence | Dataset Catalog Tool |
| EvidenceBundle | Evidence Aggregator |
| RecommendationEvidence | Recommendation Node |
| ExecutionTrace | Runtime |
| ErrorInfo | Runtime |
| Metadata | Runtime |
| GraphState | LangGraph Runtime |

No component may modify another component's model.

---

# 3.4 RuntimeContext

Represents runtime execution information.

Required fields:

- execution_id
- request_id
- runtime_mode
- workflow_version
- graph_version
- started_at
- current_node
- completed_nodes
- skipped_nodes

Optional fields:

- finished_at

Purpose:

Provides deterministic execution metadata shared across every node.

---

# 3.5 UserRequest

Represents the original user query.

Required fields:

- request_text
- language
- latitude
- longitude

Optional fields:

- village_name
- district
- province
- scenario_request

Purpose:

Represents immutable user input.

Nodes SHALL never modify this object.

---

# 3.6 WeatherEvidence

Owner:

Weather Tool

Required fields:

- temperature
- rainfall
- humidity
- wind_speed
- weather_condition
- source
- observation_time
- confidence

Purpose:

Stores current weather evidence.

---

# 3.7 ForecastEvidence

Owner:

Forecast Tool

Required fields:

- forecast_date
- discharge
- return_period
- severity
- lead_time
- source
- confidence

Purpose:

Stores flood forecast information produced by GloFAS.

---

# 3.8 GISEvidence

Owner:

GIS Analysis Tool

Required fields:

- flood_zone
- population_exposed
- infrastructure_exposed
- affected_area
- exposure_level
- confidence

Optional fields:

- raster_reference
- processing_metadata

Purpose:

Stores deterministic GIS analysis.

---

# 3.9 VillageEvidence

Owner:

Village Tool

Required fields:

- village_name
- population
- district
- province
- geometry_reference
- confidence

Purpose:

Provides village-level information.

---

# 3.10 ShelterEvidence

Owner:

Shelter Tool

Required fields:

- shelters
- nearest_shelter
- available_capacity
- confidence

Purpose:

Stores evacuation information.

---

# 3.11 KnowledgeEvidence

Owner:

Government Knowledge Tool

Required fields:

- retrieved_chunks
- citations
- confidence

Purpose:

Stores grounded government guidance.

---

# 3.12 DatasetEvidence

Owner:

Dataset Catalog Tool

Required fields:

- datasets
- provenance
- confidence

Purpose:

Stores dataset provenance and catalogue information.

---

# 3.13 EvidenceBundle

Owner:

Evidence Aggregator

Purpose:

Aggregates evidence from every completed node.

Contains:

- WeatherEvidence
- ForecastEvidence
- GISEvidence
- VillageEvidence
- ShelterEvidence
- KnowledgeEvidence
- DatasetEvidence

The Evidence Bundle SHALL NOT generate new information.

It SHALL only aggregate existing evidence.

---

# 3.14 RecommendationEvidence

Owner:

Recommendation Node

Required fields:

- recommendation
- rationale
- confidence
- citations

Optional fields:

- evacuation_priority
- supporting_evidence

Purpose:

Stores the grounded recommendation generated by the Recommendation Node.

---

# 3.15 ExecutionTrace

Owner:

Runtime

Required fields:

- node_name
- started_at
- finished_at
- duration_ms
- status
- retries
- skipped
- error

Purpose:

Provides deterministic execution history.

Exactly one ExecutionTrace SHALL exist per executed node.

---

# 3.16 ErrorInfo

Owner:

Runtime

Required fields:

- error_type
- message
- recoverable
- source_node

Optional fields:

- stack_trace

Purpose:

Stores structured runtime failures.

Errors SHALL never terminate GraphState creation.

---

# 3.17 Metadata

Owner:

Runtime

Required fields:

- graph_version
- workflow_version
- implementation_version
- generated_at

Optional fields:

- environment
- build_number

Purpose:

Stores execution metadata.

---

# 3.18 Serialization Rules

Every canonical model SHALL:

- support JSON serialization;
- support deterministic deserialization;
- avoid circular references;
- avoid runtime-only objects;
- avoid callable fields;
- avoid file handles;
- avoid mutable shared collections.

---

# 3.19 Validation Rules

Every canonical model SHALL validate:

- required fields;
- data types;
- value ranges;
- enumeration values;
- timestamp format;
- confidence values (0.0–1.0).

Invalid models SHALL fail validation immediately.

---

# 3.20 Versioning

Canonical models are versioned independently from runtime implementations.

Backward compatibility SHALL be maintained whenever possible.

Breaking changes require:

- architecture review;
- implementation contract update;
- runtime migration plan.

---

# 3.21 Summary

The canonical models defined in this section form the immutable data foundation of the Flood-Aware platform.

Every subsequent section—including GraphState, DecisionContext Mapping, Node Contracts, Runtime Contracts, Evidence Aggregation, Recommendation Generation, and Execution Trace—builds directly upon these models.

No implementation may introduce additional runtime models that duplicate or replace the canonical models without an approved Architecture Decision Record (ADR).

---

# 4. GraphState

---

## 4.1 Purpose

GraphState is the canonical state object shared across every node within the Flood-Aware LangGraph workflow.

It represents the complete execution context of a single workflow invocation and serves as the only mutable object exchanged between graph nodes.

All node communication SHALL occur exclusively through GraphState.

Nodes SHALL NOT communicate directly with each other.

---

# 4.2 Design Philosophy

GraphState exists to ensure:

- deterministic execution;
- complete traceability;
- explainable recommendations;
- immutable evidence ownership;
- fault isolation;
- reproducible AI reasoning;
- future compatibility with conversational workflows.

GraphState SHALL remain the single source of truth for every workflow execution.

---

# 4.3 GraphState Ownership

Owner:

LangGraph Runtime

Responsibilities:

- initialise state;
- distribute state to nodes;
- receive updated state;
- preserve execution history;
- provide final state to Recommendation Node;
- expose final state to AIRuntime.

No tool is permitted to construct or replace GraphState.

Only the LangGraph Runtime owns the GraphState lifecycle.

---

# 4.4 GraphState Lifecycle

The lifecycle SHALL follow the sequence below.

1. AIRuntime receives a DecisionContext.

2. DecisionContext is transformed into GraphState.

3. GraphState is initialised.

4. Entry node receives GraphState.

5. Each node reads GraphState.

6. Each node returns an updated GraphState.

7. Routing evaluates GraphState.

8. Additional nodes execute.

9. Recommendation Node receives the completed GraphState.

10. AIRuntime converts RecommendationEvidence into Recommendation.

11. GraphState is archived.

A GraphState instance SHALL represent exactly one workflow execution.

---

# 4.5 State Evolution

GraphState SHALL evolve monotonically.

Information may only be:

- added;
- validated;
- enriched.

Previously recorded evidence SHALL NEVER be overwritten.

Evidence corrections SHALL be recorded as new versions while preserving historical values.

---

# 4.6 State Immutability

GraphState SHALL be treated as logically immutable.

Each node SHALL:

- receive one GraphState;
- produce one new GraphState.

Nodes SHALL NOT mutate the received instance in place.

This guarantees deterministic replay and simplifies debugging.

---

# 4.7 Canonical Structure

GraphState SHALL contain the following logical sections.

| Section | Owner |
|----------|-------|
| RuntimeContext | Runtime |
| UserRequest | Runtime |
| WeatherEvidence | Weather Tool |
| ForecastEvidence | Forecast Tool |
| GISEvidence | GIS Tool |
| VillageEvidence | Village Tool |
| ShelterEvidence | Shelter Tool |
| KnowledgeEvidence | Government Knowledge Tool |
| DatasetEvidence | Dataset Catalog Tool |
| EvidenceBundle | Evidence Aggregator |
| RecommendationEvidence | Recommendation Node |
| ExecutionTrace | Runtime |
| ErrorInfo | Runtime |
| Metadata | Runtime |

No additional top-level sections may be introduced without an approved Architecture Decision Record (ADR).

---

# 4.8 Required Sections

Every GraphState SHALL contain:

- RuntimeContext
- UserRequest
- ExecutionTrace
- Metadata

These sections SHALL always exist, even if some tools are skipped.

---

# 4.9 Optional Sections

The following sections may be absent until produced by their corresponding node.

- WeatherEvidence
- ForecastEvidence
- GISEvidence
- VillageEvidence
- ShelterEvidence
- KnowledgeEvidence
- DatasetEvidence
- EvidenceBundle
- RecommendationEvidence

Missing optional sections SHALL NOT invalidate GraphState.

---

# 4.10 Read Rules

Every node SHALL be permitted to read every section.

Nodes SHALL NEVER assume optional sections exist.

Nodes SHALL verify required evidence before using it.

---

# 4.11 Write Rules

Each section has exactly one owner.

Only the owning node may create or update its section.

Example:

Weather Node

Allowed:

- WeatherEvidence

Not allowed:

- ForecastEvidence
- GISEvidence
- ShelterEvidence

The ownership model guarantees deterministic evidence provenance.

---

# 4.12 Append Rules

ExecutionTrace SHALL be append-only.

EvidenceBundle SHALL be append-only.

Errors SHALL be append-only.

Historical records SHALL NEVER be removed.

---

# 4.13 Recommendation Rules

RecommendationEvidence SHALL only be created by the Recommendation Node.

No previous node may:

- infer recommendations;
- calculate confidence;
- produce evacuation advice.

Every previous node exists solely to collect factual evidence.

---

# 4.14 State Validation

GraphState SHALL be validated:

- before graph execution;
- before every node execution;
- after every node execution;
- before Recommendation Node execution;
- before AIRuntime returns a Recommendation.

Invalid state SHALL terminate workflow execution safely.

---

# 4.15 Serialization

GraphState SHALL support deterministic serialisation.

It SHALL be serialisable to:

- JSON;
- API responses;
- persistent storage;
- execution logs;
- future distributed runtimes.

GraphState SHALL NOT contain:

- file handles;
- open sockets;
- database sessions;
- callable objects;
- threads;
- generators;
- runtime-only references.

---

# 4.16 Compatibility

GraphState SHALL remain compatible with:

- Sequential Planner (legacy)
- LangGraph Runtime
- AI Assistant
- Scenario Simulator
- Dashboard
- Evaluation Framework

Future extensions SHALL preserve backward compatibility whenever possible.

---

# 4.17 Performance Requirements

GraphState SHALL remain lightweight.

Nodes SHALL store only information required for downstream reasoning.

Large artefacts such as raster files, NetCDF datasets, GeoJSON files, PDFs, and embeddings SHALL be referenced through immutable identifiers rather than embedded directly within GraphState.

---

# 4.18 Security Requirements

GraphState SHALL never expose:

- API keys;
- authentication tokens;
- database credentials;
- filesystem secrets;
- internal service credentials.

Sensitive runtime information SHALL remain outside GraphState.

---

# 4.19 Thread Safety

GraphState SHALL support concurrent execution.

Each workflow invocation SHALL own exactly one GraphState instance.

GraphState instances SHALL never be shared across independent executions.

---

# 4.20 Versioning

GraphState SHALL include version metadata through RuntimeContext and Metadata.

Version information SHALL allow:

- deterministic replay;
- backward compatibility checks;
- migration between runtime versions.

Breaking changes require an approved Architecture Decision Record (ADR).

---

# 4.21 Summary

GraphState is the canonical execution object of the Flood-Aware LangGraph runtime.

It provides:

- deterministic execution;
- immutable evidence ownership;
- complete workflow traceability;
- explainable AI recommendations;
- fault isolation;
- compatibility across future sprints.

Every graph node, routing decision, evidence aggregation step, execution trace, recommendation, and future conversational workflow SHALL operate exclusively through GraphState, making it the single source of truth for the entire Flood-Aware decision pipeline.

---

# 5. DecisionContext Mapping

---

## 5.1 Purpose

This section defines the canonical transformation between the existing `DecisionContext` used by the Flood-Aware AI Runtime and the new immutable `GraphState` introduced for the LangGraph Runtime.

This mapping provides the compatibility layer that allows the LangGraph execution engine to coexist with the existing runtime without breaking previously implemented functionality.

Every workflow execution SHALL begin with this transformation.

---

# 5.2 Mapping Philosophy

The transformation SHALL satisfy the following principles.

1. Deterministic.

2. Lossless.

3. Backward compatible.

4. Immutable.

5. Framework-independent.

6. Version aware.

7. Reproducible.

The mapping SHALL NOT modify the original DecisionContext.

---

# 5.3 Source Object

Input:

DecisionContext

Owner:

AI Runtime

DecisionContext SHALL remain the external runtime contract exposed by AIRuntime.

The LangGraph Runtime SHALL NOT receive raw user input directly.

---

# 5.4 Target Object

Output:

GraphState

Owner:

LangGraph Runtime

GraphState SHALL become the only object exchanged between graph nodes.

---

# 5.5 Mapping Lifecycle

Every workflow SHALL execute the following sequence.

1. User submits request.

2. AIRuntime constructs DecisionContext.

3. Runtime validates DecisionContext.

4. DecisionContextMapper creates GraphState.

5. GraphState enters LangGraph.

6. LangGraph executes.

7. RecommendationEvidence is produced.

8. AIRuntime converts RecommendationEvidence into Recommendation.

This sequence SHALL remain identical across all execution modes.

---

# 5.6 Mapping Responsibility

The DecisionContextMapper is solely responsible for constructing GraphState.

No graph node may perform this transformation.

No tool may modify the mapping.

---

# 5.7 RuntimeContext Mapping

The RuntimeContext section SHALL be initialised from runtime metadata.

The mapper SHALL populate:

- execution identifier
- request identifier
- workflow version
- graph version
- runtime mode
- workflow start timestamp
- current node (Entry)
- completed node list (empty)
- skipped node list (empty)

The mapper SHALL generate identifiers when not provided by the caller.

---

# 5.8 UserRequest Mapping

The mapper SHALL construct an immutable UserRequest from DecisionContext.

The following information SHALL be transferred where available.

- user query
- language
- latitude
- longitude
- village name
- district
- province
- scenario request

Unavailable information SHALL be represented using approved null values rather than invented defaults.

---

# 5.9 Metadata Mapping

Metadata SHALL be initialised by the mapper.

The mapper SHALL populate:

- implementation version
- graph version
- workflow version
- generation timestamp

Metadata SHALL remain immutable for the lifetime of the workflow.

---

# 5.10 Execution Trace Mapping

ExecutionTrace SHALL be initialised as an empty collection.

No trace entries shall exist before the Entry Node begins execution.

Each subsequent node SHALL append exactly one trace entry.

---

# 5.11 Evidence Initialisation

The following sections SHALL initially be empty.

- WeatherEvidence
- ForecastEvidence
- GISEvidence
- VillageEvidence
- ShelterEvidence
- DatasetEvidence
- KnowledgeEvidence
- EvidenceBundle
- RecommendationEvidence

These sections SHALL only be populated by their owning nodes.

---

# 5.12 Error Initialisation

GraphState SHALL begin with an empty error collection.

Errors SHALL be appended only by:

- Runtime
- Router
- Graph Engine
- Tool Nodes

The mapper SHALL never create synthetic errors.

---

# 5.13 DecisionContext Compatibility Rules

The existing DecisionContext SHALL remain unchanged.

Sprint 10 SHALL NOT modify:

- DecisionContext
- Recommendation
- AIRuntime public interface
- Sequential Planner

The mapper SHALL provide compatibility instead of replacing existing runtime contracts.

---

# 5.14 Recommendation Compatibility

RecommendationEvidence produced by the Recommendation Node SHALL be translated into the existing Recommendation model before leaving the LangGraph Runtime.

This translation SHALL be performed exclusively by the AIRuntime compatibility layer.

The Recommendation Node SHALL NOT return legacy Recommendation objects.

---

# 5.15 Runtime Modes

The mapper SHALL support all approved runtime modes.

Examples include:

- Production
- Development
- Evaluation
- Testing
- Scenario Simulation

Runtime mode SHALL influence orchestration behaviour only.

It SHALL NOT alter GraphState structure.

---

# 5.16 Validation Rules

The mapper SHALL validate the incoming DecisionContext before GraphState construction.

Validation SHALL ensure:

- required fields exist
- coordinates are valid
- language values are recognised
- identifiers are unique
- runtime mode is supported

Invalid DecisionContext SHALL prevent graph execution.

---

# 5.17 Deterministic Guarantees

Given identical DecisionContext input,

the mapper SHALL always produce an identical GraphState.

No randomness is permitted.

No timestamps other than workflow creation time may be generated during mapping.

---

# 5.18 Security Rules

Sensitive runtime information SHALL NOT be copied into GraphState.

Examples include:

- API keys
- authentication tokens
- database credentials
- filesystem secrets
- service configuration

Only information required for workflow execution may be transferred.

---

# 5.19 Extension Rules

Future runtime fields SHALL be added using additive evolution.

Existing mappings SHALL remain valid.

Removing mapped fields constitutes a breaking architectural change requiring an approved Architecture Decision Record (ADR).

---

# 5.20 Summary

The DecisionContextMapper provides the canonical compatibility bridge between the legacy AI Runtime and the new LangGraph Runtime.

Its responsibilities are strictly limited to:

- validating DecisionContext;
- constructing immutable GraphState;
- initialising runtime metadata;
- preserving backward compatibility;
- enabling deterministic workflow execution.

No graph node, tool, router, or recommendation component may bypass or replace this mapping layer.

---

# 6. Node Contracts

---

## 6.1 Purpose

This section defines the canonical implementation contract for every LangGraph node within the Flood-Aware Decision Intelligence Platform.

A node represents a single deterministic execution unit responsible for performing exactly one logical task within the workflow.

Every node SHALL conform to this contract regardless of the tool it orchestrates.

---

# 6.2 Design Principles

Every node SHALL satisfy the following principles.

1. Single Responsibility Principle.

2. Deterministic execution.

3. Stateless execution.

4. Immutable input.

5. Immutable output.

6. No hidden side effects.

7. Framework independence.

8. Tool ownership isolation.

9. Fail gracefully.

10. Fully testable.

---

# 6.3 Canonical Node Interface

Every node SHALL expose one public execution operation.

The node SHALL:

- receive one immutable GraphState;
- perform its assigned responsibility;
- return one new immutable GraphState.

Nodes SHALL NOT:

- modify GraphState in place;
- return partial state;
- communicate with other nodes directly.

---

# 6.4 Node Lifecycle

Every node SHALL execute the following lifecycle.

1. Receive GraphState.

2. Validate preconditions.

3. Read required sections.

4. Execute owned tool or logic.

5. Validate produced output.

6. Update owned GraphState section.

7. Append ExecutionTrace.

8. Return updated GraphState.

Failure at any stage SHALL follow the Error Handling Contract.

---

# 6.5 Preconditions

Before execution, every node SHALL verify:

- GraphState is valid.
- Required upstream evidence exists.
- Required metadata exists.
- RuntimeContext is available.
- UserRequest is available.

If a required dependency is unavailable, the node SHALL fail gracefully.

---

# 6.6 Postconditions

After successful execution, every node SHALL guarantee:

- Owned section has been populated or updated.
- No unowned section has been modified.
- ExecutionTrace contains one new entry.
- GraphState remains valid.
- Runtime metadata remains unchanged.

---

# 6.7 Ownership Rules

Each node owns exactly one primary GraphState section.

| Node | Owned Section |
|------|---------------|
| Weather Node | WeatherEvidence |
| Forecast Node | ForecastEvidence |
| GIS Analysis Node | GISEvidence |
| Village Node | VillageEvidence |
| Shelter Node | ShelterEvidence |
| Government Knowledge Node | KnowledgeEvidence |
| Dataset Catalog Node | DatasetEvidence |
| Evidence Aggregator | EvidenceBundle |
| Recommendation Node | RecommendationEvidence |

Nodes SHALL NOT modify sections owned by another node.

---

# 6.8 Read Permissions

Nodes MAY read any existing GraphState section.

Nodes SHALL treat all read-only sections as immutable.

Reading SHALL never modify state.

---

# 6.9 Write Permissions

Nodes MAY write only:

- their owned evidence section;
- ExecutionTrace (append only);
- ErrorInfo (append only, if required).

Everything else SHALL remain unchanged.

---

# 6.10 Tool Invocation

Nodes that orchestrate tools SHALL:

- invoke exactly one primary tool;
- validate tool output;
- translate tool output into canonical evidence models;
- preserve provenance.

Tool-specific models SHALL NEVER be stored directly inside GraphState.

---

# 6.11 Deterministic Behaviour

Given identical GraphState input and identical external tool responses,

the node SHALL always produce identical GraphState output.

Randomness is prohibited.

Hidden mutable state is prohibited.

---

# 6.12 Idempotency

Node execution SHALL be idempotent.

Executing the same node multiple times with identical inputs SHALL produce identical outputs.

Nodes SHALL NOT create duplicate evidence.

---

# 6.13 Error Behaviour

Nodes SHALL distinguish between:

- recoverable failures;
- fatal failures.

Recoverable failures SHALL:

- append ErrorInfo;
- append ExecutionTrace;
- return GraphState.

Fatal failures SHALL:

- terminate graph execution safely;
- preserve ExecutionTrace;
- preserve collected evidence.

---

# 6.14 Execution Trace Requirements

Each node SHALL append exactly one ExecutionTrace entry.

The trace SHALL include:

- node name;
- execution status;
- start timestamp;
- finish timestamp;
- execution duration;
- retry count;
- skipped flag;
- associated error identifier (if applicable).

Nodes SHALL NOT modify previous trace entries.

---

# 6.15 Performance Requirements

Nodes SHALL minimise execution latency.

Recommended targets:

- local computation: <100 ms
- repository queries: <500 ms
- GIS processing: implementation dependent
- external API requests: configurable timeout
- LLM reasoning (Recommendation Node only): configurable timeout

These values are operational targets and may be tuned without changing the contract.

---

# 6.16 Logging Requirements

Nodes SHALL emit structured logs.

Logs SHOULD include:

- execution identifier;
- request identifier;
- node name;
- status;
- execution duration;
- warning messages;
- failure information.

Logs SHALL never expose sensitive information.

---

# 6.17 Security Requirements

Nodes SHALL NOT expose:

- API keys;
- credentials;
- internal configuration;
- filesystem secrets;
- infrastructure metadata.

Sensitive information SHALL remain outside GraphState.

---

# 6.18 Concurrency Requirements

Nodes SHALL support concurrent execution across independent GraphState instances.

Nodes SHALL NOT share mutable state.

Thread safety SHALL be guaranteed by design.

---

# 6.19 Testing Requirements

Every node SHALL support:

- unit testing;
- mocked tool testing;
- integration testing;
- deterministic regression testing;
- failure-path testing.

Tests SHALL not require modifications to GraphState contracts.

---

# 6.20 Extension Rules

Future nodes SHALL implement this contract without modification.

New nodes SHALL:

- own exactly one GraphState section;
- follow the node lifecycle;
- satisfy ownership rules;
- append ExecutionTrace;
- obey deterministic execution guarantees.

Existing node contracts SHALL remain backward compatible.

---

# 6.21 Summary

The Node Contract establishes a uniform execution model for every LangGraph node in the Flood-Aware platform.

By enforcing immutable state exchange, strict ownership, deterministic execution, structured tracing, and graceful failure handling, the contract ensures that every node behaves predictably and can be composed into a reliable, explainable, and maintainable decision workflow.

All present and future nodes SHALL conform to this contract.

---

# 7. Router Contracts

---

## 7.1 Purpose

The Router is responsible for determining the execution path of the LangGraph workflow.

It evaluates the current immutable GraphState and decides which node shall execute next.

The Router SHALL orchestrate workflow progression without modifying business evidence.

It SHALL remain deterministic, stateless, and independent from tool implementations.

---

# 7.2 Responsibilities

The Router SHALL be responsible for:

- selecting the next executable node;
- evaluating conditional edges;
- skipping unnecessary nodes;
- preventing invalid transitions;
- terminating the graph when execution is complete;
- preserving deterministic execution order.

The Router SHALL NOT:

- execute tools;
- modify evidence;
- call repositories;
- invoke LLMs;
- perform GIS analysis;
- perform weather analysis;
- aggregate evidence.

---

# 7.3 Design Principles

The Router SHALL satisfy the following principles.

1. Deterministic.

2. Stateless.

3. Immutable.

4. Side-effect free.

5. Explainable.

6. Testable.

7. Framework-independent.

---

# 7.4 Inputs

The Router SHALL receive exactly one immutable GraphState.

The Router SHALL read:

- RuntimeContext
- UserRequest
- WeatherEvidence
- ForecastEvidence
- GISEvidence
- VillageEvidence
- ShelterEvidence
- DatasetEvidence
- KnowledgeEvidence
- EvidenceBundle
- ErrorInfo
- ExecutionTrace

The Router SHALL NOT modify any of these sections.

---

# 7.5 Outputs

The Router SHALL produce one routing decision.

A routing decision consists of:

- next node identifier;
- execution reason;
- skipped nodes;
- termination flag.

The Router SHALL NOT return business evidence.

---

# 7.6 Routing Decision Model

Every routing decision SHALL contain:

- current node;
- next node;
- decision reason;
- evaluated conditions;
- skipped nodes;
- graph completion flag.

The routing decision SHALL be deterministic.

---

# 7.7 Execution Order

The Router SHALL preserve the approved workflow order.

The default execution order SHALL be:

1. Weather Node

2. Forecast Node

3. GIS Analysis Node

4. Village Node

5. Shelter Node

6. Government Knowledge Node

7. Dataset Catalog Node

8. Evidence Aggregator

9. Recommendation Node

Execution order SHALL only change through approved conditional routing.

---

# 7.8 Conditional Routing

The Router MAY skip nodes only when explicitly permitted by the architecture.

Typical examples include:

- GIS skipped when forecast severity is Normal.
- Knowledge Node skipped when no policy question exists.
- Dataset Node skipped when no structured datasets are required.

Skipped nodes SHALL be recorded in ExecutionTrace.

---

# 7.9 Routing Conditions

Every routing condition SHALL satisfy:

- deterministic evaluation;
- no randomness;
- no hidden state;
- no network calls;
- no repository access.

Conditions SHALL depend solely upon GraphState.

---

# 7.10 Entry Contract

The Router SHALL always begin execution from the graph entry node.

The entry node SHALL be defined by the architecture.

No node SHALL execute before the entry node.

---

# 7.11 Exit Contract

Graph execution SHALL terminate only when:

- Recommendation Node completes successfully;

OR

- Fatal failure occurs.

No additional routing decisions shall occur after graph termination.

---

# 7.12 Skip Behaviour

When a node is skipped:

the Router SHALL:

- record the skipped node;
- record the reason;
- append ExecutionTrace;
- continue graph execution.

Skipped nodes SHALL NOT generate evidence.

---

# 7.13 Retry Behaviour

The Router SHALL NOT perform retries itself.

Retry policies belong to the Runtime.

The Router SHALL only evaluate whether execution may continue after a retry result.

---

# 7.14 Error Routing

If a recoverable failure occurs:

the Router SHALL:

- continue execution where appropriate;
- bypass unavailable nodes if permitted;
- preserve collected evidence.

If a fatal failure occurs:

the Router SHALL:

- terminate execution;
- preserve GraphState;
- preserve ExecutionTrace.

---

# 7.15 Infinite Loop Prevention

The Router SHALL guarantee that graph execution terminates.

The Router SHALL prevent:

- circular routing;
- repeated node execution without reason;
- endless retries;
- recursive routing loops.

A node SHALL execute at most once unless explicitly permitted by the Runtime retry policy.

---

# 7.16 Determinism

Given identical GraphState,

the Router SHALL always produce identical routing decisions.

The Router SHALL never depend upon:

- current time;
- randomness;
- thread scheduling;
- filesystem state;
- external APIs.

---

# 7.17 Performance Requirements

Routing SHALL be lightweight.

Target latency:

- less than 5 milliseconds per routing decision.

Routing SHALL never become the computational bottleneck.

---

# 7.18 Logging Requirements

Every routing decision SHALL emit structured logs containing:

- execution identifier;
- current node;
- next node;
- routing reason;
- skipped nodes;
- termination status.

Logs SHALL never contain sensitive information.

---

# 7.19 Testing Requirements

The Router SHALL support:

- unit testing;
- routing regression tests;
- conditional edge tests;
- skip tests;
- termination tests;
- infinite-loop prevention tests;
- failure-routing tests.

All routing tests SHALL be deterministic.

---

# 7.20 Extension Rules

Future graph nodes SHALL integrate without requiring Router redesign.

Adding a node SHALL require only:

- node registration;
- routing condition definition;
- graph edge definition.

Existing routing behaviour SHALL remain backward compatible.

---

# 7.21 Summary

The Router Contract defines the deterministic orchestration behaviour of the Flood-Aware LangGraph workflow.

The Router is responsible only for workflow progression. It never performs business logic, never executes tools, and never modifies evidence.

By enforcing immutable state evaluation, deterministic routing, explicit skip behaviour, controlled termination, and framework independence, the Router ensures that every workflow execution is predictable, explainable, and fully testable.

---

# 8. Runtime Contracts

---

## 8.1 Purpose

The Runtime is responsible for orchestrating the complete lifecycle of a Flood-Aware workflow execution.

It acts as the execution engine that:

- receives requests from AIRuntime;
- constructs GraphState;
- executes the LangGraph workflow;
- coordinates Router decisions;
- manages retries and failures;
- returns RecommendationEvidence to AIRuntime.

The Runtime SHALL never perform business reasoning itself.

---

# 8.2 Runtime Responsibilities

The Runtime SHALL:

- initialise GraphState;
- execute graph nodes;
- invoke the Router;
- coordinate execution flow;
- manage retries;
- enforce execution policies;
- preserve GraphState consistency;
- collect execution traces;
- terminate workflows safely.

The Runtime SHALL NOT:

- perform weather analysis;
- perform GIS processing;
- execute repository queries directly;
- generate recommendations;
- aggregate evidence.

Those responsibilities belong to specialised nodes.

---

# 8.3 Runtime Lifecycle

Every workflow SHALL execute the following lifecycle.

1. AIRuntime receives a DecisionContext.

2. DecisionContextMapper creates GraphState.

3. Runtime validates GraphState.

4. Runtime invokes the Entry Node.

5. Router selects the next node.

6. Runtime executes the selected node.

7. Updated GraphState is validated.

8. ExecutionTrace is appended.

9. Router selects the following node.

10. Steps 6–9 repeat until termination.

11. RecommendationEvidence is returned.

12. AIRuntime converts RecommendationEvidence into the existing Recommendation model.

---

# 8.4 Runtime Inputs

The Runtime SHALL receive:

- immutable GraphState;
- Runtime configuration;
- Router implementation;
- Registered graph nodes.

No additional runtime state SHALL exist outside GraphState.

---

# 8.5 Runtime Outputs

The Runtime SHALL return:

- completed GraphState;
- RecommendationEvidence;
- ExecutionTrace;
- ErrorInfo (if present).

The Runtime SHALL NOT return partially completed workflows.

---

# 8.6 Runtime Validation

The Runtime SHALL validate GraphState:

- before execution;
- before every node;
- after every node;
- before Recommendation Node;
- before returning results.

Execution SHALL stop immediately if validation fails.

---

# 8.7 Node Invocation Contract

The Runtime SHALL invoke nodes exclusively through the GraphNode protocol.

Each invocation SHALL:

- receive one immutable GraphState;
- return one immutable GraphState.

The Runtime SHALL NOT bypass node contracts.

---

# 8.8 Retry Policy

The Runtime owns retry behaviour.

Retries SHALL be permitted only for recoverable failures.

Default retry policy:

- maximum retries: 3
- exponential backoff
- deterministic retry recording

Retry attempts SHALL be recorded in ExecutionTrace.

---

# 8.9 Timeout Policy

Every node SHALL execute within an approved timeout.

Example operational defaults:

| Node | Default Timeout |
|------|----------------:|
| Weather | 10 seconds |
| Forecast | 30 seconds |
| GIS | 120 seconds |
| Knowledge | 30 seconds |
| Recommendation | 60 seconds |

Timeout values SHALL remain configurable.

Timeouts SHALL never corrupt GraphState.

---

# 8.10 Failure Recovery

Recoverable failures SHALL:

- preserve GraphState;
- append ErrorInfo;
- append ExecutionTrace;
- continue execution when permitted by the Router.

Fatal failures SHALL:

- terminate execution;
- preserve collected evidence;
- preserve ExecutionTrace;
- return GraphState for inspection.

---

# 8.11 Execution Ordering

The Runtime SHALL preserve Router ordering exactly.

The Runtime SHALL never reorder nodes.

The Runtime SHALL never execute nodes in parallel unless explicitly approved by future architecture revisions.

Sprint 10 execution SHALL remain sequential.

---

# 8.12 GraphState Ownership

The Runtime owns GraphState for the entire workflow.

Nodes receive temporary access only.

Nodes SHALL never retain references after execution.

---

# 8.13 Recommendation Compatibility

The Runtime SHALL translate RecommendationEvidence into the existing Recommendation model before returning results to AIRuntime.

This compatibility layer SHALL remain internal to the Runtime.

Existing public APIs SHALL remain unchanged.

---

# 8.14 Logging

The Runtime SHALL emit structured logs for:

- workflow start;
- node execution;
- routing decisions;
- retries;
- skipped nodes;
- workflow completion;
- workflow failure.

Logs SHALL contain:

- execution identifier;
- request identifier;
- runtime version;
- graph version.

Sensitive information SHALL never be logged.

---

# 8.15 Performance Requirements

The Runtime SHALL introduce minimal orchestration overhead.

Operational targets:

- runtime overhead < 5% of total workflow time;
- GraphState validation < 2 ms;
- routing decision < 5 ms;
- workflow orchestration shall not become the primary performance bottleneck.

---

# 8.16 Concurrency

Each workflow SHALL execute within its own isolated Runtime context.

GraphState SHALL never be shared between concurrent executions.

The Runtime SHALL support concurrent workflow execution without shared mutable state.

---

# 8.17 Deterministic Guarantees

Given:

- identical DecisionContext;
- identical external tool responses;
- identical configuration;

the Runtime SHALL produce:

- identical GraphState;
- identical ExecutionTrace;
- identical RecommendationEvidence.

Randomness SHALL not influence execution.

---

# 8.18 Security Requirements

The Runtime SHALL never expose:

- API keys;
- authentication credentials;
- filesystem paths;
- internal service configuration;
- infrastructure secrets.

Only approved GraphState data may leave the Runtime boundary.

---

# 8.19 Testing Requirements

The Runtime SHALL support:

- unit testing;
- mocked graph execution;
- integration testing;
- deterministic replay testing;
- timeout testing;
- retry testing;
- failure-path testing;
- regression testing.

Every workflow SHALL be reproducible using recorded GraphState and ExecutionTrace.

---

# 8.20 Extension Rules

Future Runtime capabilities SHALL be additive.

Examples include:

- parallel execution;
- distributed execution;
- streaming responses;
- checkpointing;
- persistent workflow memory.

These extensions SHALL preserve:

- GraphState contracts;
- Node contracts;
- Router contracts;
- AIRuntime compatibility.

---

# 8.21 Backward Compatibility

Sprint 10 SHALL preserve the existing AIRuntime public interface.

SequentialPlanner SHALL remain available until LangGraphRuntime becomes the default execution strategy.

The Runtime SHALL allow both strategies to coexist through dependency injection.

No existing API consumers shall require modification during Sprint 10.

---

# 8.22 Summary

The Runtime Contract defines the execution engine of the Flood-Aware Decision Intelligence Platform.

It coordinates workflow execution while remaining independent of business logic, evidence generation, and AI reasoning.

By enforcing deterministic execution, immutable GraphState management, structured retries, validation, and backward compatibility, the Runtime provides a stable foundation for LangGraph integration and all future architectural evolution.

# 9. Evidence Aggregation Contracts

---

## 9.1 Purpose

The Evidence Aggregator is responsible for consolidating evidence produced by all upstream nodes into a single immutable EvidenceBundle.

It represents the only component authorised to combine evidence originating from multiple sources.

The Evidence Aggregator SHALL NOT generate new business evidence.

Its sole responsibility is to organise, validate, deduplicate, reconcile, and prepare evidence for the Recommendation Node.

---

# 9.2 Responsibilities

The Evidence Aggregator SHALL:

- collect evidence from all evidence-producing nodes;
- validate evidence completeness;
- remove duplicate evidence;
- identify conflicting evidence;
- preserve provenance;
- calculate overall evidence confidence;
- construct the immutable EvidenceBundle.

The Evidence Aggregator SHALL NOT:

- execute external tools;
- query repositories;
- invoke APIs;
- perform GIS processing;
- perform weather analysis;
- generate recommendations;
- invoke an LLM.

---

# 9.3 Inputs

The Evidence Aggregator SHALL receive the following immutable GraphState sections.

- WeatherEvidence
- ForecastEvidence
- GISEvidence
- VillageEvidence
- ShelterEvidence
- DatasetEvidence
- KnowledgeEvidence
- ErrorInfo
- ExecutionTrace

The aggregator SHALL treat every section as read-only.

---

# 9.4 Output

The aggregator SHALL produce exactly one immutable EvidenceBundle.

No additional GraphState sections shall be modified.

The Recommendation Node SHALL consume only the EvidenceBundle.

---

# 9.5 Ownership

Ownership of the EvidenceBundle belongs exclusively to the Evidence Aggregator.

No other node may modify EvidenceBundle.

The Recommendation Node SHALL consume EvidenceBundle without modification.

---

# 9.6 Aggregation Order

Evidence SHALL be aggregated using the following deterministic order.

1. Weather

2. Forecast

3. GIS

4. Village

5. Shelter

6. Dataset Catalog

7. Government Knowledge

This order SHALL remain identical across executions.

---

# 9.7 Aggregation Rules

Evidence SHALL be copied into EvidenceBundle.

The aggregator SHALL NOT transform domain meaning.

The aggregator MAY:

- reorder internally;
- normalise formatting;
- remove duplicates;
- attach provenance;
- compute aggregate confidence.

The aggregator SHALL NOT:

- invent evidence;
- remove valid evidence;
- alter factual values.

---

# 9.8 Deduplication

Duplicate evidence SHALL be removed.

Evidence is considered duplicate when all of the following match.

- source
- evidence type
- semantic meaning
- location
- timestamp

Only one canonical copy SHALL remain.

Deduplication SHALL be deterministic.

---

# 9.9 Conflict Detection

The aggregator SHALL identify conflicting evidence.

Examples include:

- conflicting flood severity;
- conflicting rainfall values;
- conflicting village risk levels;
- inconsistent infrastructure impact;
- inconsistent shelter availability.

Conflicting evidence SHALL NEVER be discarded automatically.

---

# 9.10 Conflict Recording

Every detected conflict SHALL produce a ConflictRecord.

A ConflictRecord SHALL include:

- conflict identifier;
- evidence sources;
- affected evidence;
- conflict category;
- severity;
- timestamp.

Conflict records SHALL become part of EvidenceBundle.

---

# 9.11 Conflict Resolution Policy

The Evidence Aggregator SHALL NOT resolve conflicts.

Conflict resolution belongs exclusively to the Recommendation Node.

The Recommendation Node SHALL decide:

- preferred evidence;
- uncertainty acknowledgement;
- recommendation confidence.

---

# 9.12 Provenance Preservation

Every evidence item SHALL preserve provenance.

Minimum provenance includes:

- producing node;
- producing tool;
- source dataset;
- timestamp;
- confidence;
- execution identifier.

Provenance SHALL never be removed.

---

# 9.13 Confidence Propagation

The Evidence Aggregator SHALL compute an overall evidence confidence.

The calculation SHALL consider:

- confidence of each evidence item;
- number of supporting sources;
- detected conflicts;
- missing evidence;
- failed nodes.

Confidence SHALL remain explainable.

Opaque scoring algorithms are prohibited.

---

# 9.14 Missing Evidence

Missing evidence SHALL NOT prevent aggregation.

Unavailable sections SHALL be represented explicitly.

The aggregator SHALL record:

- unavailable evidence;
- skipped nodes;
- failed nodes.

The Recommendation Node SHALL receive this information.

---

# 9.15 Partial Evidence

The aggregator SHALL support incomplete workflows.

If only a subset of evidence exists,

EvidenceBundle SHALL still be produced.

Incomplete evidence SHALL reduce confidence but SHALL NOT invalidate the workflow.

---

# 9.16 Evidence Integrity

The Evidence Aggregator SHALL preserve evidence integrity.

It SHALL NOT:

- alter measurements;
- alter coordinates;
- alter timestamps;
- alter discharge values;
- alter flood classifications;
- alter recommendations.

Evidence SHALL remain immutable.

---

# 9.17 Determinism

Given identical GraphState,

the Evidence Aggregator SHALL always produce identical EvidenceBundle output.

Random ordering is prohibited.

Hash-map iteration order SHALL NOT influence aggregation.

---

# 9.18 Performance Requirements

Aggregation SHALL remain lightweight.

Operational targets:

- aggregation latency < 10 milliseconds;
- duplicate detection O(n log n) or better;
- conflict detection deterministic.

Aggregation SHALL never dominate workflow execution time.

---

# 9.19 Logging

The Evidence Aggregator SHALL emit structured logs.

Logs SHOULD include:

- execution identifier;
- aggregated evidence count;
- duplicate count;
- conflict count;
- confidence score;
- aggregation duration.

Sensitive information SHALL never be logged.

---

# 9.20 Error Behaviour

Recoverable aggregation failures SHALL:

- append ErrorInfo;
- append ExecutionTrace;
- preserve available evidence;
- continue execution when possible.

Fatal failures SHALL:

- terminate aggregation;
- preserve GraphState;
- preserve ExecutionTrace.

---

# 9.21 Testing Requirements

The Evidence Aggregator SHALL support:

- unit testing;
- duplicate detection tests;
- conflict detection tests;
- confidence propagation tests;
- incomplete evidence tests;
- deterministic regression tests.

Identical input SHALL always produce identical aggregated output.

---

# 9.22 Extension Rules

Future evidence-producing nodes SHALL integrate without redesigning the aggregator.

Adding a new evidence source SHALL require:

- registering the evidence type;
- defining provenance rules;
- defining confidence contribution.

Existing aggregation behaviour SHALL remain backward compatible.

---

# 9.23 Summary

The Evidence Aggregator provides the canonical consolidation layer for the Flood-Aware LangGraph Runtime.

It combines independently generated evidence into a single immutable EvidenceBundle while preserving provenance, detecting conflicts, propagating confidence, and maintaining deterministic behaviour.

The Evidence Aggregator never performs reasoning, never resolves conflicts, and never generates recommendations.

Its sole responsibility is to prepare trustworthy, explainable evidence for the Recommendation Node.

# Sprint 10.2 – Evidence Aggregation

**Status:** Not Started

**Objective**

Implement the Evidence Aggregation layer that consolidates outputs from all LangGraph nodes into a single immutable `EvidenceBundle` for downstream AI reasoning.

The Evidence Aggregator shall become the only component responsible for combining evidence across tools while preserving provenance, detecting conflicts, propagating confidence, and maintaining deterministic execution.

---

## Scope

This sprint implements:

- Evidence Aggregator
- EvidenceBundle construction
- Provenance preservation
- Duplicate detection
- Conflict detection
- Confidence propagation
- Execution trace integration
- Comprehensive testing

No AI reasoning shall be implemented during this sprint.

---

# Sprint 10.2.1 – Evidence Aggregator

### Status

Not Started

### Deliverables

- [ ] Create `backend/app/graph/evidence/`
- [ ] Implement `EvidenceAggregator`
- [ ] Register aggregator in Graph Builder
- [ ] Execute after Dataset Catalog Node
- [ ] Execute before Recommendation Node
- [ ] Preserve immutable GraphState

### Definition of Done

- [ ] Aggregator implemented
- [ ] Graph compiles
- [ ] No runtime regressions

---

# Sprint 10.2.2 – Evidence Collection

### Status

Not Started

### Deliverables

Collect evidence from:

- [ ] WeatherEvidence
- [ ] ForecastEvidence
- [ ] GISEvidence
- [ ] VillageEvidence
- [ ] ShelterEvidence
- [ ] DatasetEvidence
- [ ] KnowledgeEvidence

The aggregator SHALL treat every evidence section as read-only.

### Definition of Done

- [ ] All evidence sections collected
- [ ] No mutation of source evidence

---

# Sprint 10.2.3 – EvidenceBundle Construction

### Status

Not Started

### Deliverables

Build immutable `EvidenceBundle` containing:

- [ ] Weather evidence
- [ ] Forecast evidence
- [ ] GIS evidence
- [ ] Village evidence
- [ ] Shelter evidence
- [ ] Dataset evidence
- [ ] Knowledge evidence
- [ ] Conflict records
- [ ] Aggregate confidence
- [ ] Provenance metadata

### Definition of Done

- [ ] EvidenceBundle validated
- [ ] Immutable model returned

---

# Sprint 10.2.4 – Duplicate Detection

### Status

Not Started

### Deliverables

Implement deterministic duplicate detection.

Duplicate comparison SHALL consider:

- [ ] Evidence type
- [ ] Source
- [ ] Timestamp
- [ ] Geographic location
- [ ] Semantic content

Duplicate evidence SHALL NOT appear twice inside the EvidenceBundle.

### Definition of Done

- [ ] Duplicate removal implemented
- [ ] Deterministic behaviour verified

---

# Sprint 10.2.5 – Conflict Detection

### Status

Not Started

### Deliverables

Detect conflicting evidence across tools.

Examples:

- [ ] Forecast severity mismatch
- [ ] GIS severity mismatch
- [ ] Conflicting shelter availability
- [ ] Population inconsistency
- [ ] Infrastructure inconsistency

Generate immutable `ConflictRecord` objects.

The aggregator SHALL NOT resolve conflicts.

### Definition of Done

- [ ] Conflict detection implemented
- [ ] Conflict records preserved

---

# Sprint 10.2.6 – Confidence Propagation

### Status

Not Started

### Deliverables

Compute overall evidence confidence using:

- [ ] Individual evidence confidence
- [ ] Supporting source count
- [ ] Missing evidence
- [ ] Conflict count
- [ ] Failed node count

The algorithm SHALL remain deterministic and explainable.

### Definition of Done

- [ ] Aggregate confidence calculated
- [ ] Confidence included in EvidenceBundle

---

# Sprint 10.2.7 – Provenance Preservation

### Status

Not Started

### Deliverables

Preserve provenance for every evidence item.

Minimum metadata:

- [ ] Producing node
- [ ] Producing tool
- [ ] Original source
- [ ] Timestamp
- [ ] Confidence
- [ ] Execution ID

Provenance SHALL never be discarded during aggregation.

### Definition of Done

- [ ] Provenance preserved
- [ ] Provenance verified by tests

---

# Sprint 10.2.8 – Execution Trace Integration

### Status

Not Started

### Deliverables

Append aggregation metadata into `ExecutionTrace`.

Include:

- [ ] Evidence count
- [ ] Duplicate count
- [ ] Conflict count
- [ ] Aggregate confidence
- [ ] Aggregation duration

### Definition of Done

- [ ] Execution trace updated
- [ ] Trace remains deterministic

---

# Sprint 10.2.9 – Failure Handling

### Status

Not Started

### Deliverables

Handle:

- [ ] Missing evidence
- [ ] Partial evidence
- [ ] Invalid evidence
- [ ] Corrupted evidence
- [ ] Aggregation exceptions

The aggregator SHALL preserve GraphState whenever possible.

### Definition of Done

- [ ] Graceful degradation verified
- [ ] ErrorInfo populated correctly

---

# Sprint 10.2.10 – Testing

### Status

Not Started

### Deliverables

Implement:

- [ ] Unit tests
- [ ] Duplicate detection tests
- [ ] Conflict detection tests
- [ ] Confidence propagation tests
- [ ] Missing evidence tests
- [ ] Provenance tests
- [ ] Execution trace tests
- [ ] Deterministic regression tests

### Definition of Done

- [ ] All tests pass
- [ ] Deterministic replay verified

---

# Acceptance Criteria

The sprint is complete when:

- [ ] EvidenceAggregator implemented
- [ ] Immutable EvidenceBundle produced
- [ ] Duplicate detection implemented
- [ ] Conflict detection implemented
- [ ] Confidence propagation implemented
- [ ] Provenance preserved
- [ ] ExecutionTrace integrated
- [ ] Graceful failure handling implemented
- [ ] Existing runtime behaviour preserved
- [ ] All tests pass
- [ ] Sprint 10.2 frozen

---

# Notes

This sprint introduces the canonical evidence consolidation layer for the LangGraph Runtime.

It intentionally performs **no AI reasoning**.

The resulting `EvidenceBundle` is the sole input consumed by the Recommendation Node during **Sprint 11 – LLM Reasoning & Grounded Recommendation**.

--- # 11. Execution Policies

---

## 11.1 Purpose

Execution Policies define the operational rules governing workflow execution inside the LangGraph Runtime.

These policies ensure every workflow executes safely, deterministically, efficiently, and predictably regardless of external tool behaviour.

Execution Policies SHALL be enforced by the Runtime.

Individual nodes SHALL NOT override these policies.

---

# 11.2 Policy Hierarchy

Execution policies SHALL be enforced in the following order:

1. Graph integrity
2. Runtime safety
3. Node execution
4. Retry policy
5. Timeout policy
6. Resource limits
7. Completion policy

Higher-level policies SHALL always take precedence over lower-level policies.

---

# 11.3 Deterministic Execution

Every workflow SHALL execute deterministically.

Given:

- identical GraphState;
- identical external tool responses;
- identical configuration;

the Runtime SHALL always produce:

- identical node order;
- identical EvidenceBundle;
- identical RecommendationEvidence;
- identical ExecutionTrace.

Random behaviour is prohibited.

---

# 11.4 Node Execution Policy

Each node SHALL execute at most once during a workflow.

Exceptions are permitted only when:

- Runtime retry policy authorises re-execution;
- future architecture explicitly enables iterative workflows.

Outside retry scenarios, repeated node execution is prohibited.

---

# 11.5 Sequential Execution

Sprint 10 SHALL execute nodes sequentially.

Only one node may execute at any point in time.

Parallel execution SHALL NOT be introduced before an approved architecture revision.

Future versions MAY support parallel execution without changing GraphState contracts.

---

# 11.6 Validation Policy

GraphState SHALL be validated:

- before graph execution;
- before every node execution;
- after every node execution;
- before Recommendation Node;
- before workflow completion.

Validation failures SHALL terminate execution immediately.

---

# 11.7 Retry Policy

Retries SHALL apply only to recoverable failures.

Default policy:

- maximum retries: 3;
- exponential backoff;
- retry metadata recorded in ExecutionTrace.

Retries SHALL preserve GraphState integrity.

Retries SHALL NEVER alter business evidence.

---

# 11.8 Timeout Policy

Every node SHALL execute within an approved timeout.

Recommended operational defaults:

| Node | Timeout |
|------|---------|
| Weather | 10 seconds |
| Forecast | 30 seconds |
| GIS Analysis | 120 seconds |
| Village | 10 seconds |
| Shelter | 10 seconds |
| Dataset Catalog | 10 seconds |
| Government Knowledge | 30 seconds |
| Evidence Aggregator | 10 seconds |
| Recommendation | 60 seconds |

Timeout values SHALL remain configurable.

---

# 11.9 Resource Limits

The Runtime SHALL enforce operational resource limits.

Policies include:

- maximum execution duration;
- maximum retries;
- maximum GraphState size;
- maximum execution trace size;
- maximum evidence count.

Resource exhaustion SHALL trigger controlled termination.

---

# 11.10 Memory Policy

GraphState SHALL remain immutable throughout execution.

Nodes SHALL NOT retain references after completion.

Temporary working memory SHALL exist only within the scope of node execution.

Memory leaks are prohibited.

---

# 11.11 Evidence Preservation Policy

Collected evidence SHALL never be discarded due to downstream failures.

If execution terminates unexpectedly:

- available evidence SHALL remain accessible;
- ExecutionTrace SHALL remain complete;
- ErrorInfo SHALL describe the failure.

---

# 11.12 Failure Isolation Policy

Failures SHALL remain isolated.

Failure of one node SHALL NOT corrupt:

- GraphState;
- previously collected evidence;
- ExecutionTrace;
- completed node outputs.

Only the failing node SHALL be affected.

---

# 11.13 Cancellation Policy

Workflow cancellation SHALL terminate execution safely.

Upon cancellation:

- current node SHALL stop;
- GraphState SHALL be preserved;
- ExecutionTrace SHALL be finalised;
- ErrorInfo SHALL indicate cancellation.

Partial results SHALL remain available for inspection.

---

# 11.14 Skip Policy

Nodes MAY be skipped only through approved Router decisions.

Skipped nodes SHALL:

- generate no evidence;
- append ExecutionTrace;
- include skip reason;
- preserve GraphState consistency.

---

# 11.15 Completion Policy

Workflow completion SHALL occur only when:

- Recommendation Node completes successfully;

OR

- Runtime detects a fatal execution failure.

No further node execution SHALL occur after completion.

---

# 11.16 Logging Policy

The Runtime SHALL emit structured logs for:

- workflow start;
- workflow completion;
- node execution;
- retries;
- skipped nodes;
- timeouts;
- failures.

Logs SHALL include:

- execution identifier;
- request identifier;
- runtime version;
- graph version.

Sensitive information SHALL never be logged.

---

# 11.17 Performance Policy

Execution overhead SHALL remain minimal.

Recommended operational targets:

- GraphState validation < 2 ms;
- routing decision < 5 ms;
- Evidence aggregation < 10 ms;
- orchestration overhead < 5% of total workflow duration.

---

# 11.18 Security Policy

Execution SHALL never expose:

- API credentials;
- authentication tokens;
- filesystem paths;
- infrastructure secrets;
- internal runtime configuration.

Only approved outputs may leave the Runtime boundary.

---

# 11.19 Compatibility Policy

Execution Policies SHALL remain backward compatible.

Future Runtime enhancements SHALL preserve:

- GraphState contracts;
- Node contracts;
- Router contracts;
- AIRuntime interface;
- Recommendation compatibility.

Breaking changes require a formal Architecture Decision Record (ADR).

---

# 11.20 Testing Policy

Execution Policies SHALL be verified through:

- unit tests;
- runtime integration tests;
- deterministic replay tests;
- timeout tests;
- retry tests;
- cancellation tests;
- failure-path tests;
- regression tests.

Every execution policy SHALL have corresponding automated test coverage.

---

# 11.21 Summary

Execution Policies define the operational behaviour of the Flood-Aware LangGraph Runtime.

These policies ensure every workflow executes deterministically, safely, and predictably while preserving GraphState integrity, evidence provenance, execution trace consistency, and backward compatibility.

By separating execution policy from business logic, the platform remains maintainable, testable, and extensible for future sprints, including advanced reasoning, conversational AI, scenario simulation, and production deployment.

---

# 12. Dependency Injection Contracts

---

## 12.1 Purpose

The Flood-Aware platform adopts **Dependency Injection (DI)** as the primary mechanism for constructing and wiring runtime components.

The objective is to ensure that every runtime dependency is:

- explicitly declared;
- independently testable;
- replaceable without modifying consumers;
- compliant with the Dependency Inversion Principle (DIP).

No production component shall instantiate its own runtime dependencies.

---

# 12.2 Design Principles

The dependency injection system SHALL satisfy the following principles.

1. Constructor Injection only.

2. No Service Locator pattern.

3. No global mutable runtime objects.

4. No singleton business services.

5. Dependencies are declared through protocols.

6. Concrete implementations remain hidden behind interfaces.

7. Runtime composition occurs exactly once.

---

# 12.3 Dependency Ownership

Each runtime component owns only the dependencies explicitly injected into it.

Ownership SHALL NOT be transferred between components.

The Dependency Injection container remains the sole owner responsible for object construction.

---

# 12.4 Dependency Lifetime

The following dependency lifetimes SHALL be used.

| Component | Lifetime |
|------------|----------|
| Configuration | Singleton |
| Tool Registry | Singleton |
| Graph Builder | Singleton |
| Runtime Factory | Singleton |
| Node Factory | Singleton |
| AIRuntime | Scoped |
| GraphRuntime | Scoped |
| GraphState | Per Execution |
| EvidenceBundle | Per Execution |
| ExecutionTrace | Per Execution |

Business data SHALL never be shared across workflow executions.

---

# 12.5 Dependency Injection Flow

Every workflow SHALL be composed in the following order.

```
Application Startup

↓

Configuration

↓

Repositories

↓

Infrastructure Services

↓

Tool Registry

↓

Node Factory

↓

Graph Builder

↓

Graph Runtime

↓

AIRuntime

↓

API Layer
```

No component may bypass this composition hierarchy.

---

# 12.6 Configuration Injection

Configuration SHALL be injected.

Examples include:

- application settings;
- GIS configuration;
- Weather configuration;
- Forecast configuration;
- RAG configuration;
- Runtime configuration.

Configuration SHALL remain immutable after application startup.

---

# 12.7 Repository Injection

Repositories SHALL always be injected.

Repositories SHALL NEVER be created inside:

- nodes;
- runtimes;
- services;
- use cases.

Repository implementations remain replaceable.

---

# 12.8 Tool Injection

Every graph node SHALL receive exactly one Tool implementation through constructor injection.

Example:

Weather Node

↓

Weather Tool

Forecast Node

↓

Forecast Tool

GIS Node

↓

GIS Analysis Tool

Knowledge Node

↓

Knowledge Tool

The node SHALL never construct its own tool.

---

# 12.9 Tool Registry Injection

The Runtime SHALL receive ToolRegistry through dependency injection.

Responsibilities:

- tool discovery;
- tool lookup;
- capability validation;
- metadata access.

The Runtime SHALL NOT own tool implementations.

---

# 12.10 Node Factory

A dedicated NodeFactory SHALL construct graph nodes.

Responsibilities include:

- dependency resolution;
- node creation;
- constructor validation;
- protocol enforcement.

The Runtime SHALL NEVER manually instantiate nodes.

---

# 12.11 Graph Builder

GraphBuilder SHALL be injected into GraphRuntime.

Responsibilities:

- graph construction;
- node registration;
- edge registration;
- graph compilation;
- graph validation.

GraphBuilder SHALL remain stateless after compilation.

---

# 12.12 Router Injection

The Runtime SHALL receive Router through dependency injection.

Responsibilities include:

- conditional routing;
- skip logic;
- edge selection.

Router SHALL remain independent from business services.

---

# 12.13 Evidence Aggregator Injection

GraphRuntime SHALL receive EvidenceAggregator through constructor injection.

Responsibilities:

- evidence consolidation;
- confidence propagation;
- conflict detection;
- provenance preservation.

No node may instantiate the aggregator.

---

# 12.14 Recommendation Engine Injection

RecommendationNode SHALL receive RecommendationEngine through dependency injection.

Future implementations may replace:

- OpenAI
- Gemini
- Local LLM
- Mock Engine

without changing RecommendationNode.

---

# 12.15 Runtime Factory

RuntimeFactory SHALL construct GraphRuntime.

Responsibilities include:

- injecting Builder;
- injecting Router;
- injecting Aggregator;
- injecting Recommendation Engine;
- validating runtime dependencies.

Only RuntimeFactory may create GraphRuntime instances.

---

# 12.16 AIRuntime Composition

AIRuntime SHALL receive GraphRuntime through constructor injection.

```
DecisionContext

↓

AIRuntime

↓

GraphRuntime

↓

Compiled Graph

↓

Recommendation
```

AIRuntime SHALL remain independent from graph implementation details.

---

# 12.17 Protocol Requirements

Every injected dependency SHALL expose an approved protocol.

Examples:

```
WeatherToolProtocol

ForecastToolProtocol

GISAnalysisToolProtocol

KnowledgeToolProtocol

RouterProtocol

GraphRuntimeProtocol

RecommendationEngineProtocol

EvidenceAggregatorProtocol
```

Concrete implementations SHALL never be referenced directly.

---

# 12.18 Testing Injection

Every dependency SHALL support replacement with test doubles.

Supported replacements include:

- Mock
- Fake
- Stub
- Spy

No production implementation shall be required during unit testing.

---

# 12.19 Runtime Isolation

Each workflow execution SHALL receive a fresh runtime context.

The following objects SHALL NOT be reused:

- GraphState
- EvidenceBundle
- ExecutionTrace
- ErrorInfo

Only immutable infrastructure components may be shared.

---

# 12.20 Prohibited Practices

The following practices are prohibited.

- Manual object construction inside nodes.
- Global mutable services.
- Hidden dependencies.
- Circular dependencies.
- Static service access.
- Runtime service lookup.
- Business logic inside factories.

---

# 12.21 Extension Rules

Future components SHALL integrate using constructor injection.

Adding a new tool SHALL require:

1. Tool implementation.
2. Tool protocol.
3. Node implementation.
4. Node registration.
5. Dependency registration.

No existing runtime component shall require modification.

---

# 12.22 Dependency Graph

```
Configuration
        │
        ▼
Repositories
        │
        ▼
Infrastructure Services
        │
        ▼
Tool Registry
        │
        ▼
Node Factory
        │
        ▼
Graph Builder
        │
        ▼
Router
        │
        ▼
Evidence Aggregator
        │
        ▼
Recommendation Engine
        │
        ▼
Graph Runtime
        │
        ▼
AIRuntime
        │
        ▼
FastAPI API
```

---

# 12.23 Validation Rules

During application startup the DI container SHALL verify:

- all required dependencies registered;
- no missing implementations;
- no circular dependencies;
- protocol compliance;
- graph compilation success.

Application startup SHALL fail immediately if validation fails.

---

# 12.24 Summary

Dependency Injection provides the composition backbone of the Flood-Aware platform.

All runtime components are created through explicit constructor injection, composed by dedicated factories, and exposed only through approved protocols. This architecture ensures loose coupling, high testability, deterministic runtime behaviour, and seamless replacement of implementations as the system evolves from Sprint 10 through Sprint 18 without modifying consumer components.

---

# 13. Testing Contracts

---

## 13.1 Purpose

Testing Contracts define the mandatory quality assurance requirements for every component introduced by the LangGraph Runtime.

Every implementation developed under Sprint 10 and beyond SHALL satisfy these contracts before being considered production-ready.

Testing SHALL verify:

- correctness;
- determinism;
- stability;
- backward compatibility;
- explainability;
- resilience.

Testing is considered part of the implementation—not an optional activity.

---

# 13.2 Testing Philosophy

The Flood-Aware platform follows the following testing principles.

1. Test behaviour, not implementation.

2. Every public contract must have automated tests.

3. Every bug must result in a regression test.

4. Deterministic behaviour must always be verifiable.

5. Infrastructure failures must be simulated.

6. Unit tests must not depend on external services.

7. Production workflows must be reproducible.

---

# 13.3 Testing Pyramid

Testing SHALL follow the standard engineering testing pyramid.

```
                End-to-End Tests
                      ▲
             Integration Tests
                      ▲
               Component Tests
                      ▲
                 Unit Tests
```

The majority of tests SHALL remain unit tests.

---

# 13.4 Unit Testing Contract

Every public class SHALL have dedicated unit tests.

Examples include:

- GraphState
- Router
- GraphBuilder
- GraphRuntime
- EvidenceAggregator
- RecommendationNode
- RuntimeAdapter

Each unit test SHALL verify one behaviour only.

Unit tests SHALL execute without:

- network access;
- filesystem dependencies;
- external APIs;
- LLM providers.

---

# 13.5 Node Testing Contract

Every graph node SHALL have its own test suite.

Each node SHALL be tested independently using mocked dependencies.

Minimum scenarios:

- successful execution;
- missing input;
- invalid input;
- timeout;
- dependency failure;
- empty output.

Node tests SHALL verify:

- GraphState updates;
- ExecutionTrace recording;
- ErrorInfo population;
- deterministic output.

---

# 13.6 Router Testing Contract

Router behaviour SHALL be fully deterministic.

Tests SHALL verify:

- normal routing;
- skipped GIS node;
- skipped Knowledge node;
- degraded execution routing;
- fatal routing termination.

Every routing decision SHALL be reproducible.

---

# 13.7 Graph Builder Testing Contract

GraphBuilder SHALL be tested independently.

Tests SHALL verify:

- node registration;
- edge registration;
- graph compilation;
- duplicate node rejection;
- invalid edge rejection;
- graph validation.

Compilation failures SHALL produce deterministic exceptions.

---

# 13.8 Runtime Testing Contract

GraphRuntime SHALL support isolated runtime tests.

Runtime tests SHALL verify:

- graph execution;
- node ordering;
- GraphState propagation;
- retry policy;
- timeout handling;
- cancellation;
- graceful degradation.

Runtime SHALL be tested without an external LLM.

---

# 13.9 Evidence Aggregator Testing Contract

Evidence Aggregator SHALL have dedicated tests.

Minimum scenarios:

- evidence aggregation;
- duplicate removal;
- conflict detection;
- provenance preservation;
- confidence propagation;
- partial evidence;
- missing evidence.

Every aggregated bundle SHALL remain immutable.

---

# 13.10 Recommendation Testing Contract

RecommendationNode SHALL support deterministic testing.

Tests SHALL verify:

- evidence consumption;
- recommendation creation;
- citation preservation;
- confidence generation;
- hallucination guardrails.

LLM responses SHALL be mocked during unit testing.

---

# 13.11 GraphState Testing Contract

GraphState SHALL support validation tests.

Minimum scenarios:

- creation;
- immutability;
- serialization;
- deserialization;
- version compatibility;
- validation failures.

Mutation attempts SHALL fail.

---

# 13.12 Protocol Testing Contract

Every protocol SHALL have compliance tests.

Implementations SHALL satisfy:

- GraphRuntimeProtocol
- GraphNodeProtocol
- RouterProtocol
- RecommendationEngineProtocol
- EvidenceAggregatorProtocol

Protocol conformance SHALL be verified automatically.

---

# 13.13 Integration Testing Contract

Integration tests SHALL verify complete graph execution.

Workflow:

```
DecisionContext

↓

AIRuntime

↓

GraphRuntime

↓

All Nodes

↓

Evidence Aggregator

↓

Recommendation Node

↓

Recommendation
```

Integration tests SHALL verify:

- end-to-end execution;
- GraphState integrity;
- ExecutionTrace completeness;
- Recommendation generation.

---

# 13.14 Regression Testing Contract

Every production bug SHALL receive a regression test.

Regression tests SHALL remain permanently in the test suite.

Previously fixed behaviour SHALL never regress.

---

# 13.15 Deterministic Replay Contract

Every execution SHALL support deterministic replay.

Given identical:

- DecisionContext;
- configuration;
- mocked tool outputs;

the Runtime SHALL reproduce identical:

- node execution order;
- GraphState;
- EvidenceBundle;
- Recommendation;
- ExecutionTrace.

---

# 13.16 Mocking Contract

External dependencies SHALL always be mocked during unit testing.

Examples include:

- Weather API
- GloFAS
- GIS processing
- OpenStreetMap
- Government Knowledge
- OpenAI
- Gemini

Mocks SHALL be deterministic.

---

# 13.17 Performance Testing Contract

Performance tests SHALL verify:

- graph compilation time;
- runtime latency;
- evidence aggregation latency;
- GraphState validation speed.

Performance regressions SHALL be detectable automatically.

---

# 13.18 Load Testing Contract

Load tests SHALL verify:

- concurrent executions;
- memory usage;
- execution throughput;
- runtime stability.

No shared mutable state shall appear under load.

---

# 13.19 Failure Testing Contract

Failure-path testing SHALL include:

- node timeout;
- node exception;
- missing evidence;
- corrupted evidence;
- router failure;
- recommendation failure;
- runtime interruption.

Failures SHALL preserve:

- GraphState;
- ExecutionTrace;
- ErrorInfo.

---

# 13.20 Security Testing Contract

Security tests SHALL verify:

- secrets not exposed;
- internal paths hidden;
- configuration protection;
- execution isolation;
- no sensitive logging.

---

# 13.21 Code Coverage Contract

Minimum coverage targets.

| Layer | Minimum Coverage |
|---------|-----------------:|
| Graph Runtime | 95% |
| Router | 95% |
| GraphState | 100% |
| Evidence Aggregator | 95% |
| Recommendation Node | 90% |
| Runtime Adapter | 90% |

Coverage SHALL NOT replace meaningful behavioural testing.

---

# 13.22 Continuous Integration Contract

Every pull request SHALL execute:

- formatting checks;
- import ordering;
- static analysis;
- unit tests;
- integration tests;
- regression tests.

No pull request may be merged if any mandatory test fails.

---

# 13.23 Acceptance Criteria

Sprint implementation SHALL NOT be considered complete unless:

- all required tests exist;
- all tests pass;
- no regressions introduced;
- deterministic replay verified;
- coverage targets achieved;
- CI pipeline passes successfully.

---

# 13.24 Summary

Testing Contracts establish the mandatory quality standards for the Flood-Aware LangGraph Runtime.

Every component introduced from Sprint 10 onward SHALL be verified through automated unit, integration, regression, deterministic replay, performance, and failure-path testing.

These contracts ensure that the platform remains reliable, explainable, maintainable, and production-ready while enabling safe architectural evolution throughout Sprints 10–18.

---

# 14. Versioning Contracts

---

## 14.1 Purpose

The Versioning Contracts define how every runtime contract, model, protocol, graph, and implementation evolves over time while maintaining backward compatibility.

The objective is to ensure that Flood-Aware remains maintainable throughout Sprints 10–18 and future releases without introducing breaking changes unexpectedly.

Versioning SHALL be deterministic, explicit, and fully documented.

---

# 14.2 Versioning Philosophy

Flood-Aware follows semantic versioning principles.

Every public contract SHALL have an explicit version.

Version numbers SHALL communicate:

- compatibility;
- stability;
- migration requirements;
- supported runtime behaviour.

Versioning SHALL apply equally to architecture, implementation, APIs, and runtime contracts.

---

# 14.3 Semantic Versioning

The project SHALL follow Semantic Versioning (SemVer).

```
MAJOR.MINOR.PATCH
```

Where:

- **MAJOR**
  - Breaking architectural or public API changes.
- **MINOR**
  - Backward-compatible feature additions.
- **PATCH**
  - Bug fixes, documentation improvements, refactoring, and non-breaking enhancements.

Example:

```
1.0.0
1.1.0
1.1.1
2.0.0
```

---

# 14.4 Contract Versioning

Every implementation contract SHALL include its own version identifier.

Examples include:

- GraphState Contract
- Runtime Contract
- Router Contract
- Evidence Aggregation Contract
- Recommendation Contract
- Execution Trace Contract

Contracts SHALL remain versioned independently of implementation code.

---

# 14.5 Graph Version

Each compiled LangGraph SHALL expose a Graph Version.

Example:

```
graph_version = "1.0.0"
```

The Graph Version SHALL identify:

- node topology;
- routing logic;
- supported runtime behaviour.

Any modification to graph topology SHALL increment the Graph Version.

---

# 14.6 GraphState Version

GraphState SHALL include an explicit schema version.

Example:

```
graph_state_version = "1.0"
```

The version SHALL identify the exact immutable schema used during execution.

GraphState versions SHALL remain backward compatible whenever possible.

---

# 14.7 EvidenceBundle Version

EvidenceBundle SHALL expose an explicit schema version.

Example:

```
evidence_bundle_version = "1.0"
```

Changes to evidence structure SHALL require version updates.

---

# 14.8 Execution Trace Version

ExecutionTrace SHALL expose its own version identifier.

Example:

```
execution_trace_version = "1.0"
```

Historical traces SHALL remain readable after future upgrades.

---

# 14.9 API Version

Public REST APIs SHALL expose an API version.

Example:

```
/api/v1/
```

Future breaking API changes SHALL create new API versions rather than modifying existing endpoints.

Example:

```
/api/v2/
```

---

# 14.10 Runtime Version

GraphRuntime SHALL expose a Runtime Version.

Example:

```
runtime_version = "1.0"
```

The Runtime Version identifies:

- execution engine;
- orchestration behaviour;
- supported contracts.

---

# 14.11 Recommendation Version

Recommendation outputs SHALL expose a Recommendation Version.

This ensures downstream consumers understand which recommendation schema produced the result.

---

# 14.12 Protocol Versioning

Every protocol SHALL remain backward compatible.

Examples:

- GraphRuntimeProtocol
- GraphNodeProtocol
- RouterProtocol
- RecommendationEngineProtocol
- EvidenceAggregatorProtocol

Breaking protocol changes SHALL require a major version increment.

---

# 14.13 Model Versioning

Every immutable model SHALL support version evolution.

Models include:

- GraphState
- EvidenceBundle
- Recommendation
- ExecutionTrace
- ErrorInfo

Schema migrations SHALL preserve compatibility whenever possible.

---

# 14.14 Documentation Versioning

Every major architecture document SHALL contain:

- document version;
- revision date;
- author;
- status.

Documents include:

- LANGGRAPH_ARCHITECTURE.md
- LANGGRAPH_IMPLEMENTATION_CONTRACTS.md
- CHANGELOG.md

---

# 14.15 Backward Compatibility

Minor and patch releases SHALL remain backward compatible.

Consumers using older implementations SHALL continue functioning without modification.

Breaking compatibility SHALL only occur during major releases.

---

# 14.16 Forward Compatibility

Whenever practical, older runtimes SHOULD ignore unknown fields gracefully.

Optional fields MAY be introduced without breaking existing consumers.

Required fields SHALL only be introduced through major versions.

---

# 14.17 Deprecation Policy

Deprecated features SHALL follow the lifecycle below.

```
Active

↓

Deprecated

↓

Removal Scheduled

↓

Removed
```

Deprecation SHALL always be documented before removal.

Deprecated components SHALL include migration guidance.

---

# 14.18 Migration Policy

Breaking changes SHALL include migration documentation.

Migration documentation SHALL describe:

- affected components;
- required code changes;
- compatibility considerations;
- replacement contracts.

No breaking change shall be introduced without documented migration instructions.

---

# 14.19 Release Tags

Git tags SHALL follow semantic versioning.

Examples:

```
v0.9.6

v0.10.0

v1.0.0
```

Every production release SHALL be tagged.

---

# 14.20 Changelog Policy

Every release SHALL update:

```
docs/CHANGELOG.md
```

Entries SHALL include:

- sprint number;
- release date;
- added features;
- improvements;
- fixes;
- compatibility notes.

---

# 14.21 Revision History

Architecture and implementation specifications SHALL maintain revision history.

Each revision SHALL record:

- version;
- author;
- date;
- summary of changes.

Example:

| Version | Date | Author | Summary |
|----------|------|--------|---------|
| 1.0 | 2026-07-26 | Muhammad Ilyas | Initial implementation specification |

---

# 14.22 Version Validation

Application startup SHALL validate:

- Graph Version;
- Runtime Version;
- GraphState Version;
- Contract Version;
- API Version.

Version mismatches SHALL produce deterministic startup errors.

---

# 14.23 Testing Version Compatibility

Automated tests SHALL verify:

- backward compatibility;
- schema evolution;
- API compatibility;
- serialization compatibility;
- GraphState migration;
- Recommendation compatibility.

Version regressions SHALL fail CI.

---

# 14.24 Long-Term Stability

The Versioning Contracts exist to ensure that Flood-Aware evolves safely throughout future development.

Future sprints—including LangGraph reasoning, conversational AI, scenario simulation, dashboards, evaluation, and production deployment—shall extend the platform without destabilising existing implementations.

Stable versioning guarantees predictable upgrades for developers, operators, and downstream consumers.

---

# 14.25 Summary

Versioning is a first-class architectural concern within Flood-Aware.

Every runtime component, protocol, schema, model, API, and architecture document SHALL expose explicit version information.

By adopting Semantic Versioning, maintaining backward compatibility, documenting migrations, and validating versions at runtime, the platform ensures long-term maintainability, safe evolution, and production-grade reliability across all future releases.

---

# 15. Directory Layout

---

## 15.1 Purpose

This section defines the canonical directory structure for the LangGraph Runtime introduced in Sprint 10.

The objective is to ensure:

- clear separation of concerns;
- predictable project organisation;
- high maintainability;
- minimal coupling;
- future scalability.

Every implementation SHALL follow this layout unless an Architecture Decision Record (ADR) explicitly approves a deviation.

---

# 15.2 Design Principles

The directory structure follows the following principles.

- One responsibility per package.
- Business logic separated from infrastructure.
- Runtime separated from tools.
- Nodes separated from orchestration.
- Immutable models isolated.
- Protocols separated from implementations.
- High cohesion.
- Low coupling.

---

# 15.3 Root Graph Package

```
backend/
└── app/
    └── graph/
```

The `graph/` package SHALL contain every component related to LangGraph orchestration.

No unrelated business logic SHALL be placed inside this package.

---

# 15.4 Canonical Directory Structure

```
backend/
└── app/
    └── graph/
        │
        ├── __init__.py
        │
        ├── builder.py
        ├── runtime.py
        ├── router.py
        ├── factory.py
        ├── settings.py
        │
        ├── state/
        │   ├── __init__.py
        │   ├── models.py
        │   ├── mapper.py
        │   └── validation.py
        │
        ├── nodes/
        │   ├── __init__.py
        │   ├── base.py
        │   ├── weather.py
        │   ├── forecast.py
        │   ├── gis.py
        │   ├── village.py
        │   ├── shelter.py
        │   ├── dataset.py
        │   ├── knowledge.py
        │   └── recommendation.py
        │
        ├── evidence/
        │   ├── __init__.py
        │   ├── aggregator.py
        │   ├── conflicts.py
        │   ├── confidence.py
        │   └── provenance.py
        │
        ├── execution/
        │   ├── __init__.py
        │   ├── trace.py
        │   ├── metrics.py
        │   ├── retry.py
        │   ├── timeout.py
        │   └── errors.py
        │
        ├── protocols/
        │   ├── __init__.py
        │   ├── runtime.py
        │   ├── node.py
        │   ├── router.py
        │   ├── recommendation.py
        │   └── evidence.py
        │
        ├── models/
        │   ├── __init__.py
        │   ├── evidence.py
        │   ├── recommendation.py
        │   ├── trace.py
        │   └── errors.py
        │
        ├── exceptions.py
        └── constants.py
```

---

# 15.5 Package Responsibilities

## graph/

Contains the orchestration layer.

Responsibilities:

- graph compilation;
- runtime execution;
- routing;
- dependency composition.

---

## graph/state/

Contains immutable runtime state.

Responsibilities:

- GraphState;
- validation;
- state mapping;
- serialization.

No orchestration logic SHALL exist here.

---

## graph/nodes/

Contains every LangGraph node.

One file SHALL represent one node.

Each node SHALL have a single responsibility.

---

## graph/evidence/

Contains evidence processing logic.

Responsibilities:

- aggregation;
- conflict detection;
- confidence propagation;
- provenance.

No AI reasoning SHALL exist here.

---

## graph/execution/

Contains execution management.

Responsibilities:

- execution tracing;
- retry logic;
- timeout handling;
- runtime metrics;
- execution errors.

---

## graph/protocols/

Contains every runtime protocol.

Examples:

- GraphRuntimeProtocol
- GraphNodeProtocol
- RouterProtocol
- RecommendationEngineProtocol
- EvidenceAggregatorProtocol

No concrete implementation SHALL appear here.

---

## graph/models/

Contains immutable runtime models.

Examples:

- EvidenceBundle
- RecommendationEvidence
- ConflictRecord
- ErrorInfo
- ExecutionMetrics

Business services SHALL consume these models without modification.

---

# 15.6 File Responsibilities

## builder.py

Responsible for:

- node registration;
- edge registration;
- graph compilation;
- graph validation.

---

## runtime.py

Responsible for:

- graph execution;
- state propagation;
- node scheduling;
- runtime lifecycle.

---

## router.py

Responsible for:

- conditional routing;
- skip logic;
- edge selection.

---

## factory.py

Responsible for:

- dependency construction;
- runtime creation;
- node creation.

---

## settings.py

Responsible for:

- runtime configuration;
- execution policies;
- timeout configuration.

---

## constants.py

Contains immutable runtime constants.

Examples:

- node names;
- graph version;
- default timeout values;
- execution limits.

---

## exceptions.py

Contains graph-specific exceptions.

Examples:

- GraphCompilationError
- RoutingError
- NodeExecutionError
- InvalidGraphStateError
- RuntimeConfigurationError

---

# 15.7 Naming Conventions

Directories SHALL use:

```
snake_case
```

Files SHALL use:

```
snake_case.py
```

Classes SHALL use:

```
PascalCase
```

Protocols SHALL end with:

```
Protocol
```

Models SHALL end with:

```
Model
```

Exceptions SHALL end with:

```
Error
```

---

# 15.8 Import Rules

Permitted dependency direction:

```
Protocols

↓

Models

↓

Nodes

↓

Evidence

↓

Router

↓

Runtime

↓

AIRuntime
```

Reverse dependencies are prohibited.

Circular imports are prohibited.

---

# 15.9 Testing Directory

The testing layout SHALL mirror the implementation layout.

Example:

```
backend/tests/

├── graph/
│   ├── test_builder.py
│   ├── test_runtime.py
│   ├── test_router.py
│   ├── test_state.py
│   ├── test_execution.py
│   ├── test_evidence.py
│   ├── test_nodes_weather.py
│   ├── test_nodes_forecast.py
│   ├── test_nodes_gis.py
│   ├── test_nodes_village.py
│   ├── test_nodes_shelter.py
│   ├── test_nodes_dataset.py
│   ├── test_nodes_knowledge.py
│   └── test_nodes_recommendation.py
```

The test hierarchy SHALL remain aligned with the production hierarchy.

---

# 15.10 Future Expansion

Future packages MAY include:

```
graph/agents/
graph/memory/
graph/scenarios/
graph/chat/
graph/telemetry/
graph/evaluation/
```

These SHALL follow the same architectural principles defined in this document.

---

# 15.11 Prohibited Structure

The following practices are prohibited:

- business logic inside protocols;
- node implementations inside runtime;
- runtime logic inside nodes;
- evidence aggregation inside recommendation node;
- multiple node implementations in one file;
- circular package dependencies;
- shared mutable state across packages.

---

# 15.12 Summary

The directory layout establishes a clear separation between orchestration, state management, node execution, evidence processing, execution management, protocols, and immutable models.

This organisation enables high cohesion, low coupling, predictable navigation, and long-term maintainability as Flood-Aware evolves from Sprint 10 through Sprint 18 while remaining aligned with production engineering practices.

---

# 16. Implementation Checklist

---

## 16.1 Purpose

This Implementation Checklist defines the mandatory engineering checkpoints required before, during, and after implementation of the LangGraph Runtime.

Its purpose is to ensure that every implementation:

- conforms to the approved architecture;
- preserves existing functionality;
- remains deterministic;
- maintains production quality;
- is verifiable through automated testing.

This checklist SHALL be used throughout Sprint 10 and referenced during code reviews for all subsequent AI-related sprints.

---

# 16.2 General Implementation Rules

Before writing any production code, developers SHALL verify that:

- all architectural specifications have been approved;
- implementation contracts are complete;
- no architectural ambiguity remains;
- affected interfaces are documented;
- acceptance criteria are clearly defined.

No implementation SHALL begin while architectural decisions remain unresolved.

---

# 16.3 Phase A — Graph Foundation

The following tasks constitute Phase A.

## Project Structure

- [ ] Create `backend/app/graph/`
- [ ] Create all required subpackages
- [ ] Add `__init__.py` to every package
- [ ] Verify import hierarchy

---

## Immutable Models

- [ ] Implement GraphState
- [ ] Implement RuntimeInfo
- [ ] Implement UserRequest
- [ ] Implement EvidenceBundle
- [ ] Implement RecommendationEvidence
- [ ] Implement ExecutionTrace
- [ ] Implement ErrorInfo

---

## Protocols

- [ ] GraphRuntimeProtocol
- [ ] GraphNodeProtocol
- [ ] RouterProtocol
- [ ] RecommendationEngineProtocol
- [ ] EvidenceAggregatorProtocol

---

## State Mapping

- [ ] Implement DecisionContextMapper
- [ ] Implement GraphStateFactory
- [ ] Validate mapping logic
- [ ] Preserve backward compatibility

---

## Runtime Skeleton

- [ ] Runtime factory
- [ ] Runtime builder
- [ ] Runtime configuration
- [ ] Graph compilation
- [ ] Graph validation

---

## Verification

- [ ] Project imports successfully
- [ ] Graph compiles
- [ ] Existing runtime unchanged
- [ ] Existing tests continue to pass

---

# 16.4 Phase B — Nodes & Routing

The following tasks constitute Phase B.

---

## Node Skeletons

- [ ] WeatherNode
- [ ] ForecastNode
- [ ] GISAnalysisNode
- [ ] VillageNode
- [ ] ShelterNode
- [ ] DatasetCatalogNode
- [ ] GovernmentKnowledgeNode
- [ ] RecommendationNode

---

## Router

- [ ] Conditional router
- [ ] Entry point
- [ ] Exit point
- [ ] Skip logic
- [ ] Error routing

---

## Runtime

- [ ] Execute graph
- [ ] State propagation
- [ ] Execution trace generation
- [ ] Error handling

---

## Verification

- [ ] Nodes execute individually
- [ ] Router behaves deterministically
- [ ] Graph completes
- [ ] Existing runtime still untouched

---

# 16.5 Phase C — AIRuntime Integration

The following tasks constitute Phase C.

---

## Dependency Injection

- [ ] Register GraphRuntime
- [ ] Preserve SequentialPlanner
- [ ] Runtime selection strategy
- [ ] Configuration support

---

## AIRuntime

- [ ] Inject GraphRuntime
- [ ] Preserve existing API
- [ ] Preserve Recommendation model
- [ ] Preserve DecisionContext

---

## Compatibility

- [ ] No API changes
- [ ] No endpoint changes
- [ ] No schema changes
- [ ] No client changes

---

## Verification

- [ ] Existing runtime selectable
- [ ] Graph runtime selectable
- [ ] Behaviour deterministic
- [ ] All tests pass

---

# 16.6 Code Quality Checklist

Every implementation SHALL satisfy the following.

## Architecture

- [ ] Single Responsibility Principle
- [ ] Dependency Inversion Principle
- [ ] No circular imports
- [ ] Immutable models
- [ ] Protocol-oriented design

---

## Maintainability

- [ ] Clear naming
- [ ] Small functions
- [ ] Minimal nesting
- [ ] Self-documenting code
- [ ] No duplicated logic

---

## Documentation

- [ ] Public classes documented
- [ ] Public methods documented
- [ ] Complex algorithms explained
- [ ] Runtime behaviour documented

---

# 16.7 Testing Checklist

Every implementation SHALL include automated tests.

---

## Unit Tests

- [ ] GraphState
- [ ] RuntimeInfo
- [ ] Mapper
- [ ] Router
- [ ] Every node
- [ ] EvidenceAggregator
- [ ] Runtime

---

## Integration Tests

- [ ] Complete graph execution
- [ ] Node interaction
- [ ] Evidence aggregation
- [ ] Recommendation generation

---

## Failure Tests

- [ ] Weather failure
- [ ] Forecast failure
- [ ] GIS failure
- [ ] Knowledge failure
- [ ] Timeout
- [ ] Exception propagation

---

## Regression Tests

- [ ] Existing planner
- [ ] Existing API
- [ ] Existing services
- [ ] Existing tests

---

# 16.8 Performance Checklist

The runtime SHALL satisfy the following.

- [ ] Minimal allocations
- [ ] No unnecessary copies
- [ ] Efficient routing
- [ ] Efficient state propagation
- [ ] Efficient evidence aggregation

Performance regressions SHALL be investigated before merging.

---

# 16.9 Security Checklist

Before merge:

- [ ] No hard-coded secrets
- [ ] No unsafe deserialization
- [ ] Input validation
- [ ] Output validation
- [ ] Error sanitization
- [ ] Logging review

---

# 16.10 Review Checklist

Every Pull Request SHALL verify:

- [ ] Architecture compliance
- [ ] Contract compliance
- [ ] Coding standards
- [ ] Documentation updated
- [ ] Tests added
- [ ] Existing tests passing
- [ ] No breaking changes

At least one reviewer SHALL approve before merge.

---

# 16.11 CI Checklist

The Continuous Integration pipeline SHALL verify:

- [ ] Formatting (`black`)
- [ ] Import ordering (`isort`)
- [ ] Static analysis (`ruff`)
- [ ] Type checking (future `mypy`)
- [ ] Unit tests
- [ ] Integration tests

A failed pipeline SHALL block merging.

---

# 16.12 Definition of Done

Sprint 10 implementation SHALL be considered complete only when all of the following are true.

## Architecture

- [ ] Architecture implemented exactly as specified
- [ ] No undocumented behaviour
- [ ] Contracts fully respected

---

## Quality

- [ ] Clean code
- [ ] Production quality
- [ ] No TODOs
- [ ] No debug code

---

## Compatibility

- [ ] Existing API unchanged
- [ ] Existing planner preserved
- [ ] Existing functionality unaffected

---

## Verification

- [ ] All tests passing
- [ ] CI passing
- [ ] Documentation updated
- [ ] Code review approved

---

# 16.13 Exit Criteria

Sprint 10 SHALL exit Architecture Freeze and enter Sprint 11 only when:

- the LangGraph Runtime is fully operational;
- GraphState is immutable and validated;
- all runtime contracts are implemented;
- evidence aggregation is deterministic;
- execution tracing is complete;
- AIRuntime supports runtime strategy selection;
- regression testing confirms zero functional regressions.

Only after these criteria are satisfied may the project proceed to Sprint 11 (LLM Reasoning & Grounded Recommendation).

---

# 16.14 Summary

This checklist serves as the operational quality gate for the LangGraph implementation.

It ensures that architectural decisions are translated into production-quality software through disciplined implementation, comprehensive testing, rigorous review, and measurable completion criteria. Every Sprint 10 task SHALL be evaluated against this checklist before it is considered complete.

---

---

# Section 17 – Concrete GraphState Models

## 17.1 Overview

This section defines the canonical implementation models used by the LangGraph Runtime.

These models are the implementation-level representation of the logical architecture defined in:

- `LANGGRAPH_ARCHITECTURE.md`

Every model defined here SHALL be implemented exactly once inside the production codebase.

These definitions SHALL be considered the implementation contract between:

- LangGraph Runtime
- Runtime Adapter
- AIRuntime
- Decision Engine
- Evidence Aggregator
- Future AI Reasoning Layer

No implementation SHALL modify these contracts without an approved Architecture Decision Record (ADR).

---

# 17.2 Design Principles

Every GraphState model SHALL satisfy the following principles.

## Strong Typing

Every field SHALL use an explicit type.

The use of:

- `Any`
- `dict`
- `object`

is prohibited unless explicitly approved.

---

## Immutability

All models SHALL be immutable after creation.

Implementation SHALL use frozen Pydantic v2 models.

No mutable shared state is permitted.

---

## JSON Serialization

Every model SHALL support deterministic JSON serialization.

Serialization SHALL preserve:

- field names
- ordering where applicable
- timestamps
- UUID values
- enumerations

---

## Deterministic Construction

Constructing the same model with identical inputs SHALL always produce an identical state.

---

## Validation

Every model SHALL perform validation during construction.

Invalid state SHALL never exist inside the runtime.

---

# 17.3 Canonical Model Hierarchy

The LangGraph Runtime SHALL use the following model hierarchy.

```
GraphState
│
├── RuntimeInfo
├── UserRequest
├── WeatherEvidence
├── ForecastEvidence
├── GISEvidence
├── VillageEvidence
├── ShelterEvidence
├── DatasetEvidence
├── KnowledgeEvidence
├── RecommendationEvidence
├── ExecutionTrace
├── ErrorInfo
├── GraphMetadata
├── DebugInfo
└── EvidenceBundle
```

No additional top-level models may be introduced without updating this specification.

---

# 17.4 Canonical Models

The following models SHALL exist.

| Model | Required | Owner |
|---------|----------|-------|
| RuntimeInfo | Yes | Runtime Adapter |
| UserRequest | Yes | DecisionContextMapper |
| WeatherEvidence | Yes | Weather Node |
| ForecastEvidence | Yes | Forecast Node |
| GISEvidence | Yes | GIS Analysis Node |
| VillageEvidence | Yes | Village Node |
| ShelterEvidence | Yes | Shelter Node |
| DatasetEvidence | Yes | Dataset Catalog Node |
| KnowledgeEvidence | Yes | Government Knowledge Node |
| RecommendationEvidence | Yes | Recommendation Node |
| ExecutionTrace | Yes | Graph Runtime |
| ErrorInfo | Yes | Runtime |
| GraphMetadata | Yes | Runtime |
| DebugInfo | Optional | Runtime |
| EvidenceBundle | Yes | Evidence Aggregator |
| GraphState | Yes | Runtime |

---

# 17.5 Ownership Rules

Every model SHALL have exactly one owner.

Ownership determines which component is permitted to create or modify the model.

| Model | Owner |
|---------|-------|
| RuntimeInfo | Runtime Adapter |
| UserRequest | DecisionContextMapper |
| WeatherEvidence | Weather Node |
| ForecastEvidence | Forecast Node |
| GISEvidence | GIS Analysis Node |
| VillageEvidence | Village Node |
| ShelterEvidence | Shelter Node |
| DatasetEvidence | Dataset Catalog Node |
| KnowledgeEvidence | Government Knowledge Node |
| RecommendationEvidence | Recommendation Node |
| ExecutionTrace | Graph Runtime |
| ErrorInfo | Runtime |
| GraphMetadata | Runtime |
| DebugInfo | Runtime |
| EvidenceBundle | Evidence Aggregator |
| GraphState | Graph Runtime |

No other component may mutate an owned model.

---

# 17.6 Model Relationships

Each model SHALL be independent.

Models SHALL reference one another only through GraphState.

The following dependency direction SHALL always be maintained.

```
Nodes
      │
      ▼
Evidence Models
      │
      ▼
Evidence Bundle
      │
      ▼
GraphState
      │
      ▼
Recommendation Node
```

No node may directly depend upon another node's implementation.

---

# 17.7 Required Properties

Every model SHALL satisfy the following properties.

| Property | Required |
|-----------|----------|
| Immutable | Yes |
| Pydantic v2 | Yes |
| Frozen | Yes |
| JSON Serializable | Yes |
| Hashable where applicable | Yes |
| Type Safe | Yes |
| Deterministic | Yes |

---

# 17.8 Optional Models

The following models may contain optional fields.

- DebugInfo
- ErrorInfo
- RecommendationEvidence

Optional fields SHALL always define explicit defaults.

---

# 17.9 GraphState Composition

GraphState SHALL be the only object exchanged between LangGraph nodes.

Nodes SHALL never exchange:

- dictionaries
- tuples
- arbitrary objects

Only GraphState.

---

# 17.10 Model Lifecycle

The lifecycle of every model SHALL follow this sequence.

```
Construction

↓

Validation

↓

Immutable Runtime Usage

↓

Serialization

↓

Logging / Trace

↓

Disposal
```

No mutation phase exists.

---

# 17.11 Model Versioning

All models SHALL follow semantic versioning.

Major structural changes SHALL require:

- Architecture update
- Implementation Contracts update
- Migration strategy

Minor additions SHALL preserve backward compatibility.

---

# 17.12 Extension Policy

Future models introduced during:

- Sprint 11
- Sprint 12
- Sprint 13
- Sprint 14

SHALL extend the existing hierarchy rather than replace it.

GraphState SHALL remain the root runtime object.

---

# 17.13 Backward Compatibility

The introduction of GraphState SHALL NOT require modifications to:

- Recommendation
- DecisionContext
- Existing Services
- Existing API Schemas

Compatibility SHALL be achieved through adapters.

---

# 17.14 Code Generation Requirements

Implementation SHALL generate exactly one production model corresponding to every model listed in Section 17.4.

No duplicate implementations are permitted.

---

# 17.15 Source of Truth

This section defines the canonical implementation contracts.

The corresponding production implementation SHALL mirror this specification exactly.

Where implementation and documentation differ, this document SHALL be considered authoritative until superseded by an approved Architecture Decision Record (ADR).

---

# 17.16 Summary

The Concrete GraphState Models establish the immutable, strongly typed foundation of the LangGraph Runtime.

Every runtime component SHALL communicate exclusively through GraphState and its canonical sub-models.

This ensures deterministic execution, explicit ownership, strong validation, architectural consistency, and long-term maintainability across all future development from Sprint 10 through Sprint 18.

---

---

# Section 18 – DecisionContext Mapping Specification

## 18.1 Purpose

This section defines the canonical transformation between the existing `DecisionContext` and the immutable `GraphState`.

The mapping exists to preserve complete backward compatibility with the existing Flood-Aware runtime while enabling the LangGraph orchestration layer.

The mapping SHALL be deterministic.

The mapping SHALL be the only approved mechanism for constructing a `GraphState` from application-level inputs.

No component other than the `DecisionContextMapper` may perform this transformation.

---

# 18.2 Mapping Pipeline

The runtime SHALL construct GraphState using the following pipeline.

```
Incoming Request

        │

        ▼

DecisionContext

        │

        ▼

DecisionContextMapper

        │

        ▼

Immutable GraphState

        │

        ▼

LangGraph Runtime

        │

        ▼

Graph Nodes
```

The mapper SHALL always produce a fully initialized GraphState.

Graph nodes SHALL never receive a partially initialized state.

---

# 18.3 Mapping Responsibilities

The DecisionContextMapper SHALL be responsible for:

- validating DecisionContext
- assigning runtime metadata
- assigning request metadata
- creating immutable GraphState
- applying canonical default values
- guaranteeing deterministic initialization

The mapper SHALL NOT:

- perform AI reasoning
- execute tools
- modify business logic
- call external APIs
- execute routing logic

---

# 18.4 Canonical Mapping Table

The following mapping SHALL be used.

| DecisionContext | GraphState | Required | Default Behaviour |
|-----------------|-----------|----------|-------------------|
| location | user_request.location | Yes | Direct copy |
| coordinates | user_request.coordinates | Optional | Null if unavailable |
| village_name | user_request.village_name | Optional | Null |
| district | user_request.district | Optional | Null |
| province | user_request.province | Optional | Null |
| language | user_request.language | Yes | "en" |
| scenario | user_request.scenario | Optional | Null |
| execution_mode | runtime.execution_mode | Yes | STANDARD |
| context | metadata.context | Optional | Empty dictionary |

No additional mappings may be introduced without updating this document.

---

# 18.5 Runtime Metadata Initialization

The mapper SHALL initialize RuntimeInfo using the following rules.

| Field | Source |
|--------|--------|
| runtime_id | Newly generated UUID |
| execution_id | Newly generated UUID |
| execution_mode | DecisionContext.execution_mode or STANDARD |
| created_at | Current UTC timestamp |
| runtime_version | Application version |
| graph_version | Graph implementation version |

These values SHALL be immutable for the lifetime of the graph execution.

---

# 18.6 Request Metadata Initialization

The mapper SHALL initialise UserRequest according to the following rules.

Missing optional values SHALL NOT prevent graph execution.

Required values SHALL be validated before GraphState construction.

If validation fails:

GraphState SHALL NOT be created.

Instead:

A validation error SHALL be returned to the caller.

---

# 18.7 Default Values

Where DecisionContext omits optional information, the following defaults SHALL be applied.

| GraphState Field | Default |
|------------------|---------|
| weather | Empty evidence model |
| forecast | Empty evidence model |
| gis | Empty evidence model |
| villages | Empty evidence model |
| shelters | Empty evidence model |
| datasets | Empty evidence model |
| knowledge | Empty evidence model |
| recommendation | Empty recommendation model |
| evidence_bundle | Empty bundle |
| execution_trace | Empty list |
| errors | Empty list |
| debug | Empty debug model |

No field within GraphState SHALL remain undefined.

---

# 18.8 Validation Rules

The mapper SHALL validate the following before GraphState creation.

## Required

- valid DecisionContext instance
- supported execution mode
- supported language
- valid location representation

## Optional

- coordinates
- village name
- district
- province
- scenario

Optional fields SHALL never invalidate graph construction.

---

# 18.9 Deterministic Construction

Constructing GraphState from identical DecisionContext inputs SHALL always produce identical state except for runtime-generated metadata.

The following fields are intentionally non-deterministic.

- runtime_id
- execution_id
- created_at

Every other field SHALL be identical.

---

# 18.10 Immutability

After GraphState has been created:

The original DecisionContext SHALL never be referenced again.

Graph nodes SHALL operate exclusively on GraphState.

DecisionContext SHALL be considered immutable input only.

---

# 18.11 Error Handling

If mapping fails:

Graph execution SHALL NOT begin.

Instead:

1. Validation errors SHALL be recorded.

2. GraphState SHALL NOT be constructed.

3. Runtime SHALL return an initialization failure.

Graph initialization failures SHALL never reach graph nodes.

---

# 18.12 Ownership

The DecisionContextMapper exclusively owns:

- GraphState construction
- runtime metadata initialization
- request metadata initialization
- default value assignment
- validation

No graph node may modify these objects.

---

# 18.13 Compatibility

This mapping layer guarantees complete backward compatibility with the existing Flood-Aware runtime.

SequentialPlanner SHALL continue receiving the existing DecisionContext.

LangGraph SHALL receive GraphState.

The RuntimeAdapter SHALL isolate these two representations.

Neither runtime SHALL require modifications to the other.

---

# 18.14 Future Compatibility

Future sprints SHALL extend this mapping without breaking existing behaviour.

Examples include:

- Sprint 11 – LLM reasoning metadata
- Sprint 12 – Conversation history
- Sprint 13 – Scenario overrides
- Sprint 14 – Dashboard session metadata

These additions SHALL extend GraphState only.

DecisionContext SHALL remain stable.

---

# 18.15 Summary

The DecisionContext Mapping Specification defines the canonical boundary between the existing Flood-Aware application layer and the LangGraph runtime.

By ensuring deterministic initialization, immutable state construction, explicit ownership, and complete backward compatibility, the mapper becomes the single approved entry point into the LangGraph execution pipeline.

No graph execution may begin until a valid immutable GraphState has been successfully created.

---

---

# Section 19 – Execution Trace Compatibility Specification

## 19.1 Purpose

This section defines the compatibility contract between the existing Flood-Aware execution tracing infrastructure and the LangGraph runtime.

The objective is to ensure that introducing LangGraph does not break existing logging, monitoring, diagnostics, or explainability features.

Execution Trace SHALL remain fully backward compatible throughout Sprint 10 and all subsequent releases.

---

# 19.2 Compatibility Goals

The execution trace subsystem SHALL satisfy the following goals.

- Preserve all existing execution tracing behaviour.
- Extend tracing to include graph execution metadata.
- Maintain deterministic execution records.
- Support explainability and auditing.
- Support future observability integrations.
- Require no changes to existing API consumers.

---

# 19.3 Execution Trace Lifecycle

Every graph execution SHALL follow the lifecycle below.

```
Graph Initialisation

        │

        ▼

Execution Trace Created

        │

        ▼

Node Starts

        │

        ▼

Node Completes

        │

        ▼

Trace Updated

        │

        ▼

Next Node

        │

        ▼

Graph Finished

        │

        ▼

Final Trace Persisted
```

A trace SHALL exist before the first node executes.

---

# 19.4 Trace Ownership

Execution Trace SHALL be owned exclusively by the Graph Runtime.

Nodes SHALL NOT:

- create traces
- modify existing trace records
- remove trace records

Nodes SHALL only emit execution events.

The Graph Runtime SHALL convert events into immutable trace records.

---

# 19.5 Trace Record Structure

Every node execution SHALL produce exactly one ExecutionTraceRecord.

Each record SHALL contain the following information.

| Field | Description |
|--------|-------------|
| execution_id | Unique graph execution identifier |
| node_name | Name of executed node |
| tool_name | Tool invoked by the node (if applicable) |
| status | SUCCESS, FAILED, SKIPPED or TIMEOUT |
| started_at | UTC timestamp when execution began |
| completed_at | UTC timestamp when execution completed |
| duration_ms | Execution duration in milliseconds |
| retries | Number of retry attempts |
| error_id | Reference to ErrorInfo if an error occurred |
| evidence_generated | Boolean indicating whether evidence was produced |
| output_reference | Identifier of produced evidence |
| routing_decision | Routing outcome for the node |

No additional mandatory fields may be introduced without updating this specification.

---

# 19.6 Status Values

The following execution states are approved.

| Status | Meaning |
|---------|---------|
| SUCCESS | Node completed successfully |
| FAILED | Node terminated with an unrecoverable error |
| SKIPPED | Node intentionally skipped by routing logic |
| TIMEOUT | Node exceeded execution timeout |

These values SHALL be represented using a strongly typed enumeration.

---

# 19.7 Existing Trace Compatibility

The existing SequentialPlanner execution trace SHALL remain unchanged.

SequentialPlanner SHALL continue producing its existing execution records.

LangGraph SHALL produce additional graph-level execution records.

The RuntimeAdapter SHALL expose a unified execution trace regardless of the active runtime.

Consumers SHALL NOT need to know whether execution originated from SequentialPlanner or LangGraph.

---

# 19.8 Unified Execution Trace

The RuntimeAdapter SHALL expose the following logical execution trace.

```
Execution Trace

│

├── Runtime Information

├── Planner Information

├── Node Execution Records

├── Tool Execution Records

├── Routing Decisions

├── Errors

└── Performance Metrics
```

This representation SHALL remain stable across future runtime implementations.

---

# 19.9 Trace Collection Rules

The Graph Runtime SHALL append execution records in execution order.

Execution records SHALL NEVER be reordered.

Execution records SHALL NEVER be removed during graph execution.

Execution history SHALL therefore remain deterministic and chronological.

---

# 19.10 Error Recording

If a node fails:

1. An ErrorInfo SHALL be created.

2. A FAILED ExecutionTraceRecord SHALL be appended.

3. GraphState SHALL remain valid.

4. Routing SHALL continue where permitted.

Fatal graph failures SHALL terminate execution only after recording the failure.

---

# 19.11 Performance Metrics

Every ExecutionTraceRecord SHALL include performance information.

Minimum metrics include:

- execution duration
- retry count
- timeout flag
- node status

Future releases may extend performance metrics without breaking compatibility.

---

# 19.12 Routing Visibility

Every routing decision SHALL be traceable.

The trace SHALL record:

- why a node executed
- why a node was skipped
- routing condition evaluated
- resulting graph edge

This enables complete explainability of graph execution.

---

# 19.13 Explainability Support

Execution Trace SHALL support the explainability requirements introduced in Sprint 11.

Recommendation explanations SHALL reference:

- executed nodes
- supporting evidence
- routing decisions
- execution order

Execution Trace therefore forms part of the evidence chain used for grounded AI recommendations.

---

# 19.14 Serialization

Execution Trace SHALL support deterministic serialization.

Supported formats include:

- JSON
- Structured Logs
- API Responses

Serialization SHALL preserve execution order.

---

# 19.15 Future Compatibility

Execution Trace SHALL support future extensions including:

- Sprint 11 – LLM reasoning trace
- Sprint 12 – Conversation trace
- Sprint 13 – Scenario execution trace
- Sprint 14 – Dashboard timeline
- Sprint 16 – Evaluation metrics
- Sprint 18 – Production monitoring

These additions SHALL extend the existing trace without modifying previous records.

---

# 19.16 Invariants

The following invariants SHALL always hold.

- Every graph execution SHALL have exactly one execution_id.
- Every executed node SHALL produce exactly one ExecutionTraceRecord.
- Trace records SHALL be immutable.
- Trace records SHALL remain in chronological order.
- Trace SHALL never contain duplicate node executions unless explicitly retried.
- Every recorded error SHALL reference a valid ErrorInfo object.
- Every routing decision SHALL be represented in the trace.
- Execution Trace SHALL remain valid even when graph execution terminates prematurely.

---

# 19.17 Summary

The Execution Trace Compatibility Specification ensures that LangGraph integrates seamlessly with the existing Flood-Aware observability infrastructure while preserving backward compatibility.

By making the Graph Runtime the sole owner of execution tracing, recording deterministic immutable trace records, and exposing a unified trace through the RuntimeAdapter, the system provides a stable foundation for explainability, debugging, monitoring, performance analysis, and future AI reasoning capabilities without requiring changes to existing consumers.

---

---

# Section 20 – Recommendation Compatibility Specification

## 20.1 Purpose

This section defines the compatibility contract between the existing Flood-Aware `Recommendation` domain model and the LangGraph runtime.

The objective is to ensure that the introduction of LangGraph does **not** require modifications to the existing Recommendation model while still supporting future AI reasoning capabilities.

Recommendation generation SHALL remain fully backward compatible throughout Sprint 10 and all subsequent releases.

---

# 20.2 Compatibility Goals

The Recommendation subsystem SHALL satisfy the following goals.

- Preserve the existing Recommendation domain model.
- Prevent breaking API contracts.
- Support future AI-generated recommendations.
- Separate evidence collection from AI reasoning.
- Maintain deterministic behaviour during Sprint 10.
- Enable explainability through supporting evidence.

---

# 20.3 Architectural Principle

The existing Recommendation model remains the canonical business object.

LangGraph SHALL NOT replace or modify this model.

Instead, LangGraph SHALL produce structured evidence that is later transformed into the existing Recommendation model.

```
GraphState

        │

        ▼

RecommendationEvidence

        │

        ▼

Recommendation Adapter

        │

        ▼

Existing Recommendation Model

        │

        ▼

API Response
```

---

# 20.4 Canonical Recommendation Flow

Recommendation generation SHALL follow the pipeline below.

```
Graph Execution

↓

Evidence Collection

↓

Evidence Bundle

↓

RecommendationEvidence

↓

Recommendation Adapter

↓

Recommendation

↓

API Response
```

No graph node other than the Recommendation Node may construct a Recommendation.

---

# 20.5 Existing Recommendation Model

The existing Recommendation domain model SHALL remain unchanged.

It SHALL continue to represent the application's official recommendation object.

Sprint 10 SHALL NOT:

- rename fields
- remove fields
- add fields
- change validation rules
- modify API contracts

---

# 20.6 RecommendationEvidence

The Recommendation Node SHALL produce a RecommendationEvidence object.

RecommendationEvidence is an internal runtime model.

It SHALL NOT be exposed through the public API.

RecommendationEvidence SHALL contain the information required to build a Recommendation while preserving explainability.

Typical information includes:

- supporting evidence
- confidence score
- evidence references
- execution trace references
- reasoning inputs
- source citations

RecommendationEvidence SHALL remain internal to the LangGraph runtime.

---

# 20.7 Recommendation Adapter

A Recommendation Adapter SHALL be responsible for transforming RecommendationEvidence into the existing Recommendation model.

The adapter SHALL:

- map fields deterministically
- preserve backward compatibility
- perform no AI reasoning
- perform no business logic
- validate the resulting Recommendation

Only the Recommendation Adapter may construct the public Recommendation object from RecommendationEvidence.

---

# 20.8 Ownership

Ownership SHALL be defined as follows.

| Component | Owner |
|-----------|-------|
| RecommendationEvidence | Recommendation Node |
| Recommendation Adapter | Runtime Adapter |
| Recommendation | Existing Domain Layer |

No other component may create Recommendation objects.

---

# 20.9 Deterministic Behaviour

During Sprint 10 the Recommendation Node SHALL remain deterministic.

It SHALL use:

- collected evidence
- routing results
- execution trace

It SHALL NOT call an LLM.

No AI reasoning is permitted during Sprint 10.

---

# 20.10 Explainability

RecommendationEvidence SHALL preserve complete explainability.

Every recommendation SHALL be traceable to:

- Weather evidence
- Forecast evidence
- GIS evidence
- Village evidence
- Shelter evidence
- Dataset evidence
- Government knowledge evidence

No recommendation may exist without supporting evidence.

---

# 20.11 Confidence

RecommendationEvidence SHALL contain a confidence score.

During Sprint 10 this confidence SHALL be computed deterministically from available evidence.

Future sprints may replace this calculation with AI-generated confidence while preserving the Recommendation API.

---

# 20.12 Validation Rules

Before constructing a Recommendation the adapter SHALL verify:

- RecommendationEvidence exists.
- EvidenceBundle is valid.
- Required evidence is present.
- ExecutionTrace completed successfully.
- No fatal graph errors occurred.

If validation fails:

Recommendation SHALL NOT be produced.

---

# 20.13 Error Handling

If recommendation construction fails:

1. ErrorInfo SHALL be created.
2. ExecutionTrace SHALL record the failure.
3. GraphState SHALL remain valid.
4. Runtime SHALL return a structured failure.

Recommendation failures SHALL never corrupt GraphState.

---

# 20.14 Future Compatibility

This compatibility layer enables future extensions without changing the Recommendation model.

Future enhancements include:

- Sprint 11 – LLM-generated reasoning
- Sprint 12 – Conversational recommendations
- Sprint 13 – Scenario-specific recommendations
- Sprint 14 – Dashboard visualisations
- Sprint 16 – Recommendation evaluation metrics
- Sprint 18 – Production AI monitoring

These extensions SHALL modify RecommendationEvidence only.

The Recommendation domain model SHALL remain stable.

---

# 20.15 Invariants

The following invariants SHALL always hold.

- Recommendation SHALL remain the canonical business object.
- RecommendationEvidence SHALL remain an internal runtime object.
- Recommendation Adapter SHALL be the only transformation layer.
- Recommendation SHALL never bypass the adapter.
- Recommendation SHALL never be produced without supporting evidence.
- Recommendation generation SHALL remain deterministic during Sprint 10.
- Public API contracts SHALL remain unchanged.

---

# 20.16 Summary

The Recommendation Compatibility Specification preserves the existing Flood-Aware Recommendation model while introducing LangGraph as the new orchestration runtime.

By separating RecommendationEvidence from the public Recommendation object and introducing a dedicated Recommendation Adapter, the architecture ensures complete backward compatibility, deterministic behaviour in Sprint 10, and a seamless migration path toward AI-driven reasoning in later sprints without requiring changes to existing APIs or business logic.

---

---

# Section 21 – Runtime Compatibility Rules

## 21.1 Purpose

This section defines the compatibility rules governing the coexistence of the existing Flood-Aware runtime and the new LangGraph runtime during the migration introduced in Sprint 10.

The primary objective is to ensure that introducing LangGraph does not alter existing application behaviour until the architecture is explicitly switched in a future sprint.

Sprint 10 SHALL introduce LangGraph infrastructure only.

SequentialPlanner SHALL remain the production execution strategy until an approved architecture decision enables LangGraph execution.

---

# 21.2 Runtime Architecture

During Sprint 10 the system SHALL support two orchestration strategies.

```
                    AIRuntime
                        │
                        ▼
               Runtime Strategy Layer
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
SequentialPlanner                 GraphRuntime
(Current Runtime)              (New Infrastructure)
        │                                │
        ▼                                ▼
 Existing Decision Flow         LangGraph Foundation
```

Only one runtime SHALL execute a request.

---

# 21.3 Runtime Selection

Runtime selection SHALL occur exclusively within the RuntimeAdapter.

No API endpoint, service, use case, or graph node may decide which runtime to execute.

The RuntimeAdapter SHALL be the single source of truth for runtime selection.

---

# 21.4 Active Runtime

The active runtime for Sprint 10 SHALL be:

**SequentialPlanner**

GraphRuntime SHALL exist but SHALL remain inactive unless explicitly enabled through the approved runtime configuration.

---

# 21.5 Runtime Modes

The following runtime modes are approved.

| Runtime Mode | Description |
|--------------|-------------|
| SEQUENTIAL | Existing deterministic SequentialPlanner |
| GRAPH | LangGraph execution runtime |
| AUTO | Reserved for future automatic runtime selection (not used in Sprint 10) |

During Sprint 10 only **SEQUENTIAL** SHALL be enabled in production.

---

# 21.6 RuntimeAdapter Responsibilities

The RuntimeAdapter SHALL be responsible for:

- selecting the active runtime
- constructing GraphState when required
- preserving backward compatibility
- normalising runtime outputs
- exposing a unified execution interface

The RuntimeAdapter SHALL NOT:

- perform AI reasoning
- execute business logic
- modify Recommendation objects
- perform routing decisions

---

# 21.7 Compatibility Requirements

Introducing GraphRuntime SHALL NOT require modifications to:

- API endpoints
- FastAPI routers
- Services
- Use Cases
- Existing Recommendation model
- Existing DecisionContext model
- Existing business logic

The runtime replacement SHALL remain transparent to all higher application layers.

---

# 21.8 Unified Runtime Interface

Both runtimes SHALL implement the same logical execution contract.

```
DecisionContext
        │
        ▼
RuntimeAdapter
        │
        ▼
Runtime Strategy
        │
        ▼
Recommendation
```

Regardless of the selected runtime, the returned Recommendation SHALL conform to the existing domain model.

---

# 21.9 SequentialPlanner Compatibility

SequentialPlanner SHALL continue to operate exactly as implemented before Sprint 10.

No behavioural changes are permitted.

No public interfaces may be modified.

No regression in execution behaviour is acceptable.

SequentialPlanner SHALL serve as the reference implementation against which GraphRuntime is validated.

---

# 21.10 GraphRuntime Compatibility

GraphRuntime SHALL initially provide infrastructure only.

During Sprint 10 it SHALL:

- compile successfully
- construct GraphState
- execute node skeletons
- maintain execution traces
- preserve runtime compatibility

It SHALL NOT:

- perform AI reasoning
- replace SequentialPlanner
- modify recommendations
- alter production execution

---

# 21.11 Runtime Output Compatibility

Both runtimes SHALL produce logically equivalent outputs.

The following SHALL remain identical regardless of runtime.

- Recommendation model
- API response schema
- Error response schema
- Logging format
- Execution identifiers
- Trace accessibility

Implementation details may differ internally but SHALL remain invisible to consumers.

---

# 21.12 Runtime Fallback

If GraphRuntime is selected but cannot initialise successfully:

1. Graph initialisation SHALL terminate safely.
2. The RuntimeAdapter SHALL record the failure.
3. If fallback is enabled, execution SHALL continue using SequentialPlanner.
4. If fallback is disabled, a structured runtime error SHALL be returned.

Fallback behaviour SHALL be deterministic.

---

# 21.13 Configuration

Runtime selection SHALL be configurable.

The runtime configuration SHALL support the following values.

| Configuration | Runtime |
|---------------|---------|
| SEQUENTIAL | SequentialPlanner |
| GRAPH | GraphRuntime |
| AUTO | Reserved for future use |

No other configuration values are permitted.

---

# 21.14 Migration Strategy

Runtime migration SHALL occur incrementally.

Sprint 10

- Graph infrastructure only

Sprint 11

- Recommendation Node gains LLM reasoning

Sprint 12

- Conversational runtime

Sprint 13

- Scenario-aware runtime

Only after successful validation may GraphRuntime become the production execution strategy.

---

# 21.15 Testing Requirements

Every implementation SHALL verify:

- Sequential runtime remains functional.
- Graph runtime initialises successfully.
- RuntimeAdapter selects the correct runtime.
- Runtime fallback behaves deterministically.
- API behaviour remains unchanged.
- Existing regression tests continue to pass.

---

# 21.16 Invariants

The following invariants SHALL always hold.

- Exactly one runtime executes a request.
- Runtime selection occurs only within RuntimeAdapter.
- SequentialPlanner remains the production runtime throughout Sprint 10.
- GraphRuntime SHALL remain behaviourally isolated until explicitly enabled.
- Recommendation output SHALL remain backward compatible.
- Existing APIs SHALL require no modification.
- Runtime replacement SHALL remain transparent to application consumers.

---

# 21.17 Summary

The Runtime Compatibility Rules define the controlled coexistence of the existing SequentialPlanner and the new GraphRuntime.

By introducing the RuntimeAdapter as the single runtime selection layer and preserving the existing Recommendation, DecisionContext, and API contracts, Sprint 10 establishes the infrastructure required for LangGraph without affecting production behaviour.

This staged migration enables the project to evolve safely from a deterministic orchestration strategy to a graph-based architecture while maintaining complete backward compatibility throughout the transition.

---