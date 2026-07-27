"""Factories for fully initialized immutable graph state."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.graph.state import (
    Coordinate,
    GraphMetadata,
    GraphState,
    RuntimeInfo,
    RuntimeMode,
    UserRequest,
)


class GraphStateFactory:
    """Create validated, fully initialized state for one graph execution."""

    def __init__(
        self,
        *,
        uuid_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] | None = None,
        workflow_version: str = "10.1",
        graph_version: str = "10.1",
        implementation_version: str = "10.1",
    ) -> None:
        """Initialize factory collaborators and immutable version metadata."""
        self._uuid_factory = uuid_factory
        self._clock = clock or (lambda: datetime.now(UTC))
        self._workflow_version = workflow_version
        self._graph_version = graph_version
        self._implementation_version = implementation_version

    def create(
        self,
        *,
        request_text: str = "",
        language: str = "en",
        coordinates: Coordinate | None = None,
        village_name: str | None = None,
        district: str | None = None,
        province: str | None = None,
        scenario_request: str | None = None,
        runtime_mode: RuntimeMode = RuntimeMode.LIVE,
    ) -> GraphState:
        """Create one complete graph state with documented empty sections."""
        timestamp = self._clock()
        runtime = RuntimeInfo(
            execution_id=self._uuid_factory(),
            request_id=self._uuid_factory(),
            runtime_mode=runtime_mode,
            workflow_version=self._workflow_version,
            graph_version=self._graph_version,
            started_at=timestamp,
        )
        metadata = GraphMetadata(
            graph_version=self._graph_version,
            workflow_version=self._workflow_version,
            implementation_version=self._implementation_version,
            generated_at=timestamp,
        )
        return GraphState(
            runtime=runtime,
            user_request=UserRequest(
                request_text=request_text,
                language=language,
                coordinates=coordinates,
                village_name=village_name,
                district=district,
                province=province,
                scenario_request=scenario_request,
            ),
            metadata=metadata,
        )
