"""Focused integration tests for graph dependency composition."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from backend.app.ai.models import ToolResult
from backend.app.decision.models import (
    Decision,
    DecisionConfidence,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)
from backend.app.data.models import DatasetMetadata, DatasetStatistics
from backend.app.dtos.datasets import (
    DatasetCatalogDTO,
    DatasetSummaryDTO,
    ShelterDTO,
    ShelterListDTO,
    VillageDTO,
    VillageListDTO,
)
from backend.app.graph.container import GraphContainer, GraphDependencies
from backend.app.graph.state import Coordinate
from backend.app.gis.geometry import BoundingBox
from backend.app.models.enums import FloodSeverity
from backend.app.rag.models import Citation, GroundedAnswer
from backend.tests.graph_test_support import forecast_result, state_factory


def test_container_wires_production_boundaries_into_the_graph() -> None:
    """The composition root should invoke each supplied boundary exactly once."""
    weather_tool = Mock()
    weather_tool.get_current_weather.return_value = SimpleNamespace(
        temperature=22.5,
        rainfall=1.2,
        humidity=80,
        wind_speed=3.0,
        weather_condition="Rain",
        source="OpenWeatherMap",
        timestamp=datetime(2026, 7, 26, tzinfo=UTC),
    )
    forecast_provider = Mock()
    forecast_provider.get_forecast.return_value = forecast_result()
    classification_service = Mock()
    classification_service.classify.return_value = FloodSeverity.MAJOR
    spatial_policy_service = Mock()
    spatial_policy_service.analysis_bounds.return_value = BoundingBox(
        min_latitude=33.9,
        min_longitude=71.4,
        max_latitude=34.1,
        max_longitude=71.6,
    )
    gis_request_factory = Mock()
    gis_request = Mock()
    gis_request_factory.build.return_value = gis_request
    gis_domain_service = AsyncMock()
    gis_domain_service.execute.return_value = SimpleNamespace(
        flood_zone=SimpleNamespace(severity=FloodSeverity.MAJOR),
        population_exposure=SimpleNamespace(exposed_population=1200.0),
        infrastructure_impact=SimpleNamespace(critical_assets_affected=3),
        flood_area_square_meters=2500.0,
        confidence=0.8,
    )
    village_tool = Mock()
    village_tool.execute.return_value = ToolResult(
        tool_name="VillageTool",
        summary="Village dataset retrieved.",
        data=VillageListDTO(
            villages=(VillageDTO(name="Mingora", district="Swat", population=1000),)
        ),
    )
    shelter_tool = Mock()
    shelter_tool.execute.return_value = ToolResult(
        tool_name="ShelterTool",
        summary="Shelter dataset retrieved.",
        data=ShelterListDTO(
            shelters=(ShelterDTO(name="School Hall", district="Swat", capacity=200),)
        ),
    )
    dataset_catalog_tool = Mock()
    dataset_catalog_tool.execute.return_value = ToolResult(
        tool_name="DatasetCatalogTool",
        summary="Dataset catalog retrieved.",
        data=DatasetCatalogDTO(
            villages=DatasetSummaryDTO(
                metadata=DatasetMetadata(
                    name="villages",
                    description="Graph test village records.",
                    version="1.0.0",
                    source="graph-test-villages.csv",
                    created_at=datetime(2026, 7, 26, tzinfo=UTC),
                    updated_at=datetime(2026, 7, 26, tzinfo=UTC),
                ),
                statistics=DatasetStatistics(record_count=1),
            ),
            shelters=DatasetSummaryDTO(
                metadata=DatasetMetadata(
                    name="shelters",
                    description="Graph test shelter records.",
                    version="1.0.0",
                    source="graph-test-shelters.csv",
                    created_at=datetime(2026, 7, 26, tzinfo=UTC),
                    updated_at=datetime(2026, 7, 26, tzinfo=UTC),
                ),
                statistics=DatasetStatistics(record_count=1),
            ),
        ),
    )
    knowledge_tool = Mock()
    knowledge_tool.answer.return_value = GroundedAnswer(
        text="Use preparedness guidance.",
        citations=(Citation("NDMA Plan", 4, "Preparedness"),),
    )
    decision_agent = AsyncMock()
    decision_agent.decide.return_value = Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH, rationale="Flood evidence"
        ),
        recommendation=Recommendation(summary="Prepare response."),
        confidence=DecisionConfidence.HIGH,
    )
    container = GraphContainer(
        GraphDependencies(
            weather_tool=weather_tool,
            forecast_provider=forecast_provider,
            flood_classification_service=classification_service,
            spatial_policy_service=spatial_policy_service,
            gis_request_factory=gis_request_factory,
            gis_domain_service=gis_domain_service,
            village_tool=village_tool,
            shelter_tool=shelter_tool,
            dataset_catalog_tool=dataset_catalog_tool,
            knowledge_tool=knowledge_tool,
            decision_agent=decision_agent,
        )
    )
    state = state_factory().create(
        request_text="What is the flood outlook?",
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249),
    )

    updated = asyncio.run(container.graph_runtime.execute(state))

    weather_tool.get_current_weather.assert_called_once()
    forecast_provider.get_forecast.assert_called_once_with(34.0151, 71.5249)
    assert classification_service.classify.call_count == 2
    assert all(
        call.args == (forecast_provider.get_forecast.return_value,)
        for call in classification_service.classify.call_args_list
    )
    spatial_policy_service.analysis_bounds.assert_called_once()
    gis_request_factory.build.assert_called_once()
    gis_domain_service.execute.assert_awaited_once_with(gis_request)
    village_tool.execute.assert_called_once()
    shelter_tool.execute.assert_called_once()
    dataset_catalog_tool.execute.assert_called_once()
    knowledge_tool.answer.assert_called_once_with("What is the flood outlook?")
    decision_agent.decide.assert_awaited_once()
    decision_call = decision_agent.decide.await_args
    assert decision_call.args[0] == updated.evidence_bundle
    assert "execution_context" in decision_call.kwargs
    execution_context = decision_call.kwargs["execution_context"]
    assert execution_context is not None
    assert execution_context.execution_id == updated.runtime.execution_id
    assert execution_context.request_id == updated.runtime.request_id
    assert updated.forecast_result is forecast_provider.get_forecast.return_value
    assert updated.gis.population_exposed == 1200.0
    assert updated.villages[0].village_name == "Mingora"
    assert updated.shelters.shelters == ("School Hall",)
    assert updated.datasets.datasets == ("villages", "shelters")
    assert updated.knowledge.citations == ("NDMA Plan:p4:Preparedness",)
    assert updated.evidence_bundle.weather is updated.weather
    assert updated.evidence_bundle.gis is updated.gis
    assert updated.recommendation.recommendation == "Prepare response."
