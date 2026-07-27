"""Map legacy decision context into immutable graph state."""

from collections.abc import Mapping

from backend.app.ai.models import DecisionContext
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.state import Coordinate, GraphState, RuntimeMode


class DecisionContextMapper:
    """Construct canonical graph state without changing legacy context."""

    def __init__(self, state_factory: GraphStateFactory) -> None:
        """Initialize the sole state-construction dependency."""
        self._state_factory = state_factory

    def map(
        self,
        context: DecisionContext,
        *,
        runtime_mode: RuntimeMode = RuntimeMode.LIVE,
    ) -> GraphState:
        """Map supported legacy context values to their graph-state fields."""
        if not isinstance(context, DecisionContext):
            raise TypeError("context must be a DecisionContext")
        values = self._context_values(context)
        return self._state_factory.create(
            request_text=self._string_value(values, "question"),
            language=self._string_value(values, "language", default="en"),
            coordinates=self._coordinates(values),
            village_name=self._optional_string_value(values, "village_name"),
            district=self._optional_string_value(values, "district"),
            province=self._optional_string_value(values, "province"),
            scenario_request=self._optional_string_value(values, "scenario"),
            runtime_mode=runtime_mode,
        )

    @staticmethod
    def _context_values(context: DecisionContext) -> Mapping[str, object]:
        """Return the only supported, immutable legacy metadata source."""
        if isinstance(context.context, Mapping):
            return context.context
        return {}

    @staticmethod
    def _coordinates(values: Mapping[str, object]) -> Coordinate | None:
        latitude = values.get("latitude")
        longitude = values.get("longitude")
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            return None
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            return Coordinate(latitude=float(latitude), longitude=float(longitude))
        return None

    @staticmethod
    def _optional_string_value(values: Mapping[str, object], key: str) -> str | None:
        value = values.get(key)
        return value if isinstance(value, str) else None

    @classmethod
    def _string_value(
        cls,
        values: Mapping[str, object],
        key: str,
        *,
        default: str = "",
    ) -> str:
        return cls._optional_string_value(values, key) or default
