"""Map graph request facts into legacy tool execution context."""

from backend.app.ai.models import DecisionContext
from backend.app.graph.state import GraphState


class ToolContextMapper:
    """Create the immutable legacy context expected by configured data tools."""

    @staticmethod
    def to_domain(state: GraphState) -> DecisionContext:
        """Return the supported request context without deriving new facts."""
        values: dict[str, object] = {
            "question": state.user_request.request_text,
            "language": state.user_request.language,
        }
        coordinates = state.user_request.coordinates
        if coordinates is not None:
            values["latitude"] = coordinates.latitude
            values["longitude"] = coordinates.longitude
        if state.user_request.village_name is not None:
            values["village_name"] = state.user_request.village_name
        if state.user_request.district is not None:
            values["district"] = state.user_request.district
        if state.user_request.province is not None:
            values["province"] = state.user_request.province
        return DecisionContext(context=values)
