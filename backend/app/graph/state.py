"""Immutable canonical state models for LangGraph execution."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.decision.models import Decision
from backend.app.forecast.models import ForecastResult


class _FrozenModel(BaseModel):
    """Provide immutable, strict, JSON-serializable graph model behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeMode(str, Enum):
    """Identify whether a graph execution uses live or scenario data."""

    LIVE = "live"
    SCENARIO = "scenario"


class GraphStatus(str, Enum):
    """Represent the lifecycle status of one graph execution."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    """Represent the lifecycle status of one graph node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class Coordinate(_FrozenModel):
    """Represent a validated WGS84 coordinate."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RuntimeInfo(_FrozenModel):
    """Store immutable execution metadata owned by the runtime."""

    execution_id: UUID
    request_id: UUID
    runtime_mode: RuntimeMode
    workflow_version: str
    graph_version: str
    started_at: datetime
    current_node: str | None = None
    completed_nodes: tuple[str, ...] = ()
    skipped_nodes: tuple[str, ...] = ()
    finished_at: datetime | None = None

    @field_validator("started_at", "finished_at")
    @classmethod
    def validate_utc_timestamp(cls, value: datetime | None) -> datetime | None:
        """Require timezone-aware UTC timestamps."""
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("timestamps must be UTC")
        return value


class UserRequest(_FrozenModel):
    """Store immutable request data available to graph nodes."""

    request_text: str = ""
    language: str = "en"
    coordinates: Coordinate | None = None
    village_name: str | None = None
    district: str | None = None
    province: str | None = None
    scenario_request: str | None = None


class _Evidence(_FrozenModel):
    """Provide shared immutable evidence fields."""

    confidence: float | None = Field(default=None, ge=0, le=1)


class WeatherEvidence(_Evidence):
    """Represent weather evidence owned by the weather node."""

    temperature: float | None = None
    rainfall: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0)
    weather_condition: str | None = None
    source: str | None = None
    observation_time: datetime | None = None


class ForecastEvidence(_Evidence):
    """Represent hydrological evidence owned by the forecast node."""

    forecast_date: datetime | None = None
    discharge: float | None = Field(default=None, ge=0)
    return_period: str | None = None
    severity: str | None = None
    lead_time: int | None = Field(default=None, ge=0)
    source: str | None = None
    snapshot_age_hours: float | None = Field(default=None, ge=0)
    snapshot_stale: bool | None = None


class GISEvidence(_Evidence):
    """Represent deterministic GIS evidence owned by the GIS node."""

    flood_zone: str | None = None
    population_exposed: float | None = Field(default=None, ge=0)
    infrastructure_exposed: int | None = Field(default=None, ge=0)
    affected_area: float | None = Field(default=None, ge=0)
    exposure_level: str | None = None
    raster_reference: str | None = None
    processing_metadata: tuple[str, ...] = ()


class VillageEvidence(_Evidence):
    """Represent village evidence owned by the village node."""

    village_name: str | None = None
    population: int | None = Field(default=None, ge=0)
    district: str | None = None
    province: str | None = None
    geometry_reference: str | None = None


class ShelterEvidence(_Evidence):
    """Represent shelter evidence owned by the shelter node."""

    shelters: tuple[str, ...] = ()
    nearest_shelter: str | None = None
    available_capacity: int | None = Field(default=None, ge=0)


class DatasetEvidence(_Evidence):
    """Represent dataset provenance owned by the dataset catalog node."""

    datasets: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()


class KnowledgeEvidence(_Evidence):
    """Represent government knowledge evidence owned by the knowledge node."""

    retrieved_chunks: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()


class RecommendationEvidence(_Evidence):
    """Represent internal deterministic recommendation evidence."""

    recommendation: str | None = None
    rationale: str | None = None
    risk_level: str | None = None
    recommended_actions: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    evacuation_priority: str | None = None
    supporting_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()


class ExecutionTrace(_FrozenModel):
    """Represent the immutable trace record for one executed graph node."""

    node_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float = Field(ge=0)
    status: NodeStatus
    retries: int = Field(ge=0)
    skipped: bool
    error: str | None = None

    @model_validator(mode="after")
    def validate_time_order(self) -> "ExecutionTrace":
        """Ensure a trace cannot finish before it starts."""
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


class ErrorInfo(_FrozenModel):
    """Represent a structured runtime error without mutating graph state."""

    error_type: str
    message: str
    recoverable: bool
    source_node: str
    stack_trace: str | None = None


class GraphMetadata(_FrozenModel):
    """Store versioned runtime metadata."""

    graph_version: str
    workflow_version: str
    implementation_version: str
    generated_at: datetime
    environment: str | None = None
    build_number: str | None = None


class DebugInfo(_FrozenModel):
    """Store optional, serializable debug information for an execution."""

    messages: tuple[str, ...] = ()


class EvidenceProvenance(_FrozenModel):
    """Describe the immutable origin of one collected evidence section."""

    evidence_type: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    source: str | None = None
    observed_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: tuple[str, ...] = ()


class EvidenceDuplicate(_FrozenModel):
    """Record a repeated external reference while retaining every origin."""

    reference: str = Field(min_length=1)
    origins: tuple[EvidenceProvenance, ...] = Field(min_length=2)


class EvidenceObservation(_FrozenModel):
    """Represent one factual value involved in an unresolved disagreement."""

    evidence_type: str = Field(min_length=1)
    value: str = Field(min_length=1)
    origin: EvidenceProvenance


class EvidenceConflict(_FrozenModel):
    """Record incompatible evidence values without resolving them."""

    subject: str = Field(min_length=1)
    observations: tuple[EvidenceObservation, ...] = Field(min_length=2)


class EvidenceBundle(_FrozenModel):
    """Aggregate immutable node evidence without creating or resolving facts."""

    weather: WeatherEvidence = Field(default_factory=WeatherEvidence)
    forecast: ForecastEvidence = Field(default_factory=ForecastEvidence)
    gis: GISEvidence = Field(default_factory=GISEvidence)
    villages: tuple[VillageEvidence, ...] = ()
    shelters: ShelterEvidence = Field(default_factory=ShelterEvidence)
    knowledge: KnowledgeEvidence = Field(default_factory=KnowledgeEvidence)
    datasets: DatasetEvidence = Field(default_factory=DatasetEvidence)
    provenance: tuple[EvidenceProvenance, ...] = ()
    duplicates: tuple[EvidenceDuplicate, ...] = ()
    conflicts: tuple[EvidenceConflict, ...] = ()


class GraphState(_FrozenModel):
    """Represent the complete immutable state of one graph execution."""

    runtime: RuntimeInfo
    user_request: UserRequest
    weather: WeatherEvidence = Field(default_factory=WeatherEvidence)
    forecast_result: ForecastResult | None = None
    forecast: ForecastEvidence = Field(default_factory=ForecastEvidence)
    gis: GISEvidence = Field(default_factory=GISEvidence)
    villages: tuple[VillageEvidence, ...] = ()
    shelters: ShelterEvidence = Field(default_factory=ShelterEvidence)
    datasets: DatasetEvidence = Field(default_factory=DatasetEvidence)
    knowledge: KnowledgeEvidence = Field(default_factory=KnowledgeEvidence)
    evidence_bundle: EvidenceBundle = Field(default_factory=EvidenceBundle)
    decision: Decision | None = None
    recommendation: RecommendationEvidence = Field(
        default_factory=RecommendationEvidence
    )
    execution_trace: tuple[ExecutionTrace, ...] = ()
    errors: tuple[ErrorInfo, ...] = ()
    metadata: GraphMetadata
    debug: DebugInfo = Field(default_factory=DebugInfo)

    @property
    def forecast_evidence(self) -> ForecastEvidence:
        """Expose the existing forecast evidence under its semantic name.

        The ``forecast`` field remains the serialized compatibility contract.
        ``forecast_result`` separately retains the canonical domain object for
        downstream orchestration without reconstructing it from evidence.
        """

        return self.forecast
