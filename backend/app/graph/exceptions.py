"""Structured failures raised by graph-layer orchestration nodes."""


class GraphNodeError(Exception):
    """Base exception for deterministic graph-node orchestration failures."""


class GISAnalysisNodeError(GraphNodeError):
    """Base exception for GIS analysis-node input and orchestration failures."""


class MissingForecastResultError(GISAnalysisNodeError):
    """Raised when GIS analysis starts without a canonical forecast result."""


class MissingCoordinatesError(GISAnalysisNodeError):
    """Raised when GIS analysis starts without requested graph coordinates."""


class WeatherNodeError(GraphNodeError):
    """Base exception for weather-node orchestration failures."""


class MissingWeatherCoordinatesError(WeatherNodeError):
    """Raised when weather retrieval starts without graph coordinates."""


class KnowledgeNodeError(GraphNodeError):
    """Base exception for government-knowledge node orchestration failures."""


class MissingKnowledgeContextError(KnowledgeNodeError):
    """Raised when knowledge retrieval starts without a user question."""
