"""Central immutable version metadata for runtime observability."""

from dataclasses import dataclass

SYSTEM_VERSION = "0.1.0"
GRAPH_VERSION = "v1.0.0"
DECISION_VERSION = "v1.0.0"
PROMPT_VERSION = "v1.0.0"


@dataclass(frozen=True, slots=True)
class VersionMetadata:
    """Describe stable versions attached to one execution context.

    This value object owns version labels only. It does not select runtime
    behaviour, modify prompts, or perform release management.
    """

    system: str = SYSTEM_VERSION
    graph: str = GRAPH_VERSION
    decision: str = DECISION_VERSION
    prompt: str = PROMPT_VERSION
