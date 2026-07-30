"""Focused orchestration tests for the remaining production graph tool nodes."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.app.ai.dataset_catalog_tool import DatasetCatalogTool
from backend.app.ai.models import ToolResult
from backend.app.ai.shelter_tool import ShelterTool
from backend.app.ai.village_tool import VillageTool
from backend.app.data.models import DatasetMetadata, DatasetStatistics
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageDTO,
    VillageListDTO,
)
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.mappers import (
    DatasetEvidenceMapper,
    KnowledgeEvidenceMapper,
    ShelterEvidenceMapper,
    ToolContextMapper,
    VillageEvidenceMapper,
    WeatherEvidenceMapper,
    WeatherRequestMapper,
)
from backend.app.graph.nodes import (
    DatasetCatalogNode,
    GovernmentKnowledgeNode,
    ShelterNode,
    VillageNode,
    WeatherNode,
)
from backend.app.graph.state import Coordinate
from backend.app.rag.knowledge_tool import KnowledgeTool
from backend.app.rag.models import Citation, GroundedAnswer
from backend.app.weather.weather_tool import WeatherTool


def _state(*, coordinates: Coordinate | None = None, question: str = "Flood outlook?"):
    """Create graph state with only the request facts required by these nodes."""
    return GraphStateFactory().create(request_text=question, coordinates=coordinates)


def _weather_result() -> SimpleNamespace:
    """Return immutable-shape weather facts from the mocked production tool."""
    return SimpleNamespace(
        temperature=22.5,
        rainfall=1.2,
        humidity=80,
        wind_speed=3.0,
        weather_condition="Rain",
        source="OpenWeatherMap",
        timestamp=datetime(2026, 7, 26, tzinfo=UTC),
    )


def test_weather_node_uses_mappers_and_updates_only_weather() -> None:
    """Weather orchestration should invoke one tool and retain factual evidence."""
    weather_tool = Mock(spec=WeatherTool)
    weather_tool.get_current_weather.return_value = _weather_result()
    node = WeatherNode(weather_tool)
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    with (
        patch.object(
            WeatherRequestMapper,
            "to_domain",
            wraps=WeatherRequestMapper.to_domain,
        ) as request_mapper,
        patch.object(
            WeatherEvidenceMapper,
            "to_graph",
            wraps=WeatherEvidenceMapper.to_graph,
        ) as evidence_mapper,
    ):
        updated = asyncio.run(node.execute(state))

    request_mapper.assert_called_once_with(state.user_request.coordinates)
    weather_tool.get_current_weather.assert_called_once()
    evidence_mapper.assert_called_once_with(
        weather_tool.get_current_weather.return_value
    )
    assert updated.weather.temperature == 22.5
    assert updated.gis is state.gis
    assert updated is not state


def test_weather_node_skips_missing_coordinates_without_tool_execution() -> None:
    """Weather skips expected coordinate-less requests without invoking its tool."""
    weather_tool = Mock(spec=WeatherTool)
    state = _state()

    updated = asyncio.run(WeatherNode(weather_tool).execute(state))

    assert updated is state
    weather_tool.get_current_weather.assert_not_called()


def test_village_node_maps_tool_result_and_preserves_unowned_state() -> None:
    """Village orchestration should map exactly the configured village facts."""
    village_tool = Mock(spec=VillageTool)
    village_tool.execute.return_value = ToolResult(
        tool_name="VillageTool",
        summary="Village dataset retrieved.",
        data=VillageListDTO(
            villages=(
                VillageDTO(
                    name="Mingora",
                    district="Swat",
                    population=1000,
                    latitude=34.7700,
                    longitude=72.3600,
                ),
            )
        ),
    )
    state = _state()

    with (
        patch.object(
            ToolContextMapper,
            "to_domain",
            wraps=ToolContextMapper.to_domain,
        ) as context_mapper,
        patch.object(
            VillageEvidenceMapper,
            "to_graph",
            wraps=VillageEvidenceMapper.to_graph,
        ) as evidence_mapper,
    ):
        updated = asyncio.run(VillageNode(village_tool).execute(state))

    context_mapper.assert_called_once_with(state)
    village_tool.execute.assert_called_once()
    evidence_mapper.assert_called_once_with(village_tool.execute.return_value.data)
    assert updated.villages[0].village_name == "Mingora"
    assert updated.weather is state.weather
    assert updated is not state


def test_shelter_node_maps_tool_result_without_ranking() -> None:
    """Shelter orchestration should preserve configured shelter order only."""
    shelter_tool = Mock(spec=ShelterTool)
    shelter_tool.execute.return_value = ToolResult(
        tool_name="ShelterTool",
        summary="Shelter dataset retrieved.",
        data=ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name="School Hall",
                    district="Swat",
                    capacity=200,
                    latitude=34.7800,
                    longitude=72.3700,
                ),
            )
        ),
    )
    state = _state()

    with patch.object(
        ShelterEvidenceMapper,
        "to_graph",
        wraps=ShelterEvidenceMapper.to_graph,
    ) as evidence_mapper:
        updated = asyncio.run(ShelterNode(shelter_tool).execute(state))

    shelter_tool.execute.assert_called_once()
    evidence_mapper.assert_called_once_with(shelter_tool.execute.return_value.data)
    assert updated.shelters.shelters == ("School Hall",)
    assert updated.villages is state.villages


def test_dataset_node_maps_catalog_provenance() -> None:
    """Dataset orchestration should retain configured names and provenance only."""
    timestamp = datetime(2026, 7, 26, tzinfo=UTC)
    catalog = DatasetCatalogDTO(
        villages=DatasetSummaryDTO(
            metadata=DatasetMetadata(
                name="Villages",
                description="Flood-Aware village records.",
                version="1.0.0",
                source="Flood-Aware villages.csv",
                created_at=timestamp,
                updated_at=timestamp,
            ),
            statistics=DatasetStatistics(record_count=150),
        ),
        shelters=DatasetSummaryDTO(
            metadata=DatasetMetadata(
                name="Shelters",
                description="Flood-Aware shelter records.",
                version="1.0.0",
                source="Flood-Aware shelters.csv",
                created_at=timestamp,
                updated_at=timestamp,
            ),
            statistics=DatasetStatistics(record_count=51),
        ),
    )
    dataset_tool = Mock(spec=DatasetCatalogTool)
    dataset_tool.execute.return_value = ToolResult(
        tool_name="DatasetCatalogTool",
        summary="Dataset catalog retrieved.",
        data=catalog,
    )
    state = _state()

    with patch.object(
        DatasetEvidenceMapper,
        "to_graph",
        wraps=DatasetEvidenceMapper.to_graph,
    ) as evidence_mapper:
        updated = asyncio.run(DatasetCatalogNode(dataset_tool).execute(state))

    dataset_tool.execute.assert_called_once()
    evidence_mapper.assert_called_once_with(catalog)
    assert updated.datasets.datasets == ("Villages", "Shelters")
    assert updated.datasets.provenance == (
        "Villages:v1.0.0 (source: Flood-Aware villages.csv)",
        "Shelters:v1.0.0 (source: Flood-Aware shelters.csv)",
    )
    assert updated.knowledge is state.knowledge


def test_knowledge_node_maps_grounded_citations_only() -> None:
    """Knowledge orchestration should preserve authoritative citations in order."""
    knowledge_tool = Mock(spec=KnowledgeTool)
    answer = GroundedAnswer(
        text="Use preparedness guidance.",
        citations=(Citation("NDMA Plan", 4, "Preparedness"),),
    )
    knowledge_tool.answer.return_value = answer
    state = _state(question="What guidance applies?")

    with patch.object(
        KnowledgeEvidenceMapper,
        "to_graph",
        wraps=KnowledgeEvidenceMapper.to_graph,
    ) as evidence_mapper:
        updated = asyncio.run(GovernmentKnowledgeNode(knowledge_tool).execute(state))

    knowledge_tool.answer.assert_called_once_with("What guidance applies?")
    evidence_mapper.assert_called_once_with(answer)
    assert updated.knowledge.citations == ("NDMA Plan:p4:Preparedness",)
    assert updated.datasets is state.datasets


def test_knowledge_node_skips_missing_question_without_tool_execution() -> None:
    """Knowledge skips an empty question without invoking its tool."""
    knowledge_tool = Mock(spec=KnowledgeTool)
    state = _state(question=" ")

    updated = asyncio.run(GovernmentKnowledgeNode(knowledge_tool).execute(state))

    assert updated is state
    knowledge_tool.answer.assert_not_called()


@pytest.mark.parametrize(
    "node",
    (
        WeatherNode,
        VillageNode,
        ShelterNode,
        DatasetCatalogNode,
        GovernmentKnowledgeNode,
    ),
)
def test_production_nodes_require_constructor_injection(node: type) -> None:
    """Production node construction must never silently select a dependency."""
    with pytest.raises(TypeError):
        node()


@pytest.mark.parametrize(
    "node,tool,method,node_name",
    (
        (WeatherNode, WeatherTool, "get_current_weather", "weather"),
        (VillageNode, VillageTool, "execute", "village"),
        (ShelterNode, ShelterTool, "execute", "shelter"),
        (DatasetCatalogNode, DatasetCatalogTool, "execute", "dataset"),
        (GovernmentKnowledgeNode, KnowledgeTool, "answer", "knowledge"),
    ),
)
def test_node_dependency_failures_become_recoverable_graph_errors(
    node: type,
    tool: type,
    method: str,
    node_name: str,
) -> None:
    """Production dependency failures must become recoverable graph errors."""
    dependency = Mock(spec=tool)
    getattr(dependency, method).side_effect = LookupError("dependency failure")
    state = _state(coordinates=Coordinate(latitude=34.0151, longitude=71.5249))

    updated = asyncio.run(node(dependency).execute(state))

    assert updated.errors[-1].error_type == "LookupError"
    assert updated.errors[-1].message == "dependency failure"
    assert updated.errors[-1].recoverable is True
    assert updated.errors[-1].source_node == node_name
