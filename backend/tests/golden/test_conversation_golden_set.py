"""Golden-set evaluation of grounded multi-turn conversation. Costs real API calls."""

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.app.ai.models import ToolResult
from backend.app.conversation.orchestrator import ConversationOrchestrator
from backend.app.conversation.session_store import ConversationSessionStore
from backend.app.decision.dependencies import build_openai_decision_provider
from backend.app.decision.evidence_reference_index import EvidenceReferenceIndex
from backend.app.decision.models import ActionRecommendation, Decision
from backend.app.decision.prompt_builder import PromptBuilder
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
from backend.app.graph.factory import GraphStateFactory
from backend.app.graph.state import Coordinate, EvidenceBundle, UserRequest
from backend.app.gis.geometry import BoundingBox
from backend.app.models.enums import FloodSeverity
from backend.app.rag.models import Citation, GroundedAnswer
from backend.tests.graph_test_support import forecast_result

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_GOLDEN_SET") != "1",
        reason="Golden-set tests call the real OpenAI API; set RUN_GOLDEN_SET=1 to run.",
    ),
]


def _all_references(decision: Decision) -> set[str]:
    """Collect every citation-like reference from a Decision, all fields."""
    references = set(decision.recommendation.citations)
    references.update(decision.recommendation.supporting_evidence)
    for item in (*decision.recommendation.actions, *decision.reasons):
        references.update(item.evidence_references)
    return references


def _assert_grounded(decision: Decision, evidence: EvidenceBundle) -> None:
    """Assert the parser-approved decision contains current-bundle citations."""
    assert decision.recommendation.citations
    assert _all_references(decision).issubset(EvidenceReferenceIndex.build(evidence))


def _shelter_related_references(evidence: EvidenceBundle) -> set[str]:
    """Return every allowed reference that identifies shelter evidence.

    Matches by what evidence a reference identifies, not by free-text
    keywords in an action description — a genuinely shelter-focused action
    naming a specific real shelter need not contain the literal word
    "shelter".
    """
    allowed = EvidenceReferenceIndex.build(evidence)
    return {
        ref
        for ref in allowed
        if "shelter" in ref.lower()
        or ref in evidence.shelters.shelters
        or ref == evidence.shelters.nearest_shelter
    }


def _is_shelter_grounded(
    action: ActionRecommendation, shelter_related: set[str]
) -> bool:
    """Return whether one action cites at least one shelter-related reference."""
    return bool(set(action.evidence_references) & shelter_related)


def _build_orchestrator(provider):
    """Compose a real graph runtime with deterministic non-LLM tool boundaries."""
    weather_tool = Mock()
    weather_tool.get_current_weather.return_value = SimpleNamespace(
        temperature=23.0,
        rainfall=48.0,
        humidity=78.0,
        wind_speed=4.0,
        weather_condition="Rain",
        source="Golden Weather Fixture",
        timestamp=datetime(2026, 7, 28, tzinfo=UTC),
    )
    forecast_provider = Mock()
    forecast_provider.get_forecast.return_value = forecast_result(
        discharge_m3_per_second=2400.0
    )
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
    gis_request_factory.build.return_value = Mock()
    gis_domain_service = AsyncMock()
    gis_domain_service.execute.return_value = SimpleNamespace(
        flood_zone=SimpleNamespace(severity=FloodSeverity.MAJOR),
        population_exposure=SimpleNamespace(exposed_population=1800.0),
        infrastructure_impact=SimpleNamespace(critical_assets_affected=4),
        flood_area_square_meters=3200.0,
        confidence=0.8,
    )
    village_tool = Mock()
    village_tool.execute.side_effect = _village_result
    shelter_tool = Mock()
    shelter_tool.execute.side_effect = _shelter_result
    dataset_catalog_tool = Mock()
    dataset_catalog_tool.execute.return_value = ToolResult(
        tool_name="DatasetCatalogTool",
        summary="Golden catalog retrieved.",
        data=DatasetCatalogDTO(
            villages=DatasetSummaryDTO(
                metadata=DatasetMetadata(
                    name="villages",
                    description="Golden village records.",
                    version="1.0.0",
                    source="golden-villages.csv",
                    created_at=datetime(2026, 7, 28, tzinfo=UTC),
                    updated_at=datetime(2026, 7, 28, tzinfo=UTC),
                ),
                statistics=DatasetStatistics(record_count=1),
            ),
            shelters=DatasetSummaryDTO(
                metadata=DatasetMetadata(
                    name="shelters",
                    description="Golden shelter records.",
                    version="1.0.0",
                    source="golden-shelters.csv",
                    created_at=datetime(2026, 7, 28, tzinfo=UTC),
                    updated_at=datetime(2026, 7, 28, tzinfo=UTC),
                ),
                statistics=DatasetStatistics(record_count=1),
            ),
        ),
    )
    knowledge_tool = Mock()
    knowledge_tool.answer.return_value = GroundedAnswer(
        text="Follow local preparedness guidance.",
        citations=(Citation("PDMA Flood Preparedness Plan", 3, "Shelters"),),
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
            decision_agent=provider,
        )
    )
    session_store = ConversationSessionStore()
    orchestrator = ConversationOrchestrator(
        graph_runtime=container.graph_runtime,
        decision_agent=provider,
        prompt_builder=PromptBuilder(),
        session_store=session_store,
        state_factory=GraphStateFactory(),
    )
    return orchestrator, session_store, {
        "weather": weather_tool,
        "forecast": forecast_provider,
        "gis": gis_domain_service,
        "village": village_tool,
        "shelter": shelter_tool,
        "knowledge": knowledge_tool,
        "dataset": dataset_catalog_tool,
    }


def _village_result(context) -> ToolResult:
    """Return locality-specific deterministic village data from graph context."""
    village_name = context.context["village_name"]
    return ToolResult(
        tool_name="VillageTool",
        summary="Golden village retrieved.",
        data=VillageListDTO(
            villages=(
                VillageDTO(
                    name=village_name,
                    district="Swat",
                    population=18000,
                    latitude=34.7700,
                    longitude=72.3600,
                ),
            )
        ),
    )


def _shelter_result(context) -> ToolResult:
    """Return a deterministic shelter whose name is tied to graph context."""
    village_name = context.context["village_name"]
    return ToolResult(
        tool_name="ShelterTool",
        summary="Golden shelter retrieved.",
        data=ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name=f"{village_name} Community Shelter",
                    district="Swat",
                    capacity=500,
                    latitude=34.7700,
                    longitude=72.3600,
                ),
            )
        ),
    )


def _request(question: str, village_name: str) -> UserRequest:
    """Create one realistic Swat request with stable location context."""
    return UserRequest(
        request_text=question,
        coordinates=Coordinate(latitude=34.0151, longitude=71.5249),
        village_name=village_name,
        district="Swat",
        province="Khyber Pakhtunkhwa",
    )


def _tool_call_counts(tools: dict[str, object]) -> dict[str, int]:
    """Return one count per injected graph tool boundary."""
    return {
        "weather": tools["weather"].get_current_weather.call_count,
        "forecast": tools["forecast"].get_forecast.call_count,
        "gis": tools["gis"].execute.await_count,
        "village": tools["village"].execute.call_count,
        "shelter": tools["shelter"].execute.call_count,
        "knowledge": tools["knowledge"].answer.call_count,
        "dataset": tools["dataset"].execute.call_count,
    }


@pytest.fixture(scope="module")
def provider():
    """Build the real, unmocked OpenAI provider used by Golden-set evaluation."""
    return build_openai_decision_provider()


class TestConversationGoldenSet:
    async def test_same_context_follow_up_reuses_evidence_and_stays_grounded(
        self, provider
    ):
        orchestrator, session_store, tools = _build_orchestrator(provider)
        session_id, _ = await orchestrator.handle_turn(
            None,
            _request("What is the flood outlook for Mingora?", "Mingora"),
        )
        _, second = await orchestrator.handle_turn(
            session_id,
            _request("What about shelters near there?", "Mingora"),
        )

        assert _tool_call_counts(tools) == {
            "weather": 1,
            "forecast": 1,
            "gis": 1,
            "village": 1,
            "shelter": 1,
            "knowledge": 1,
            "dataset": 1,
        }
        session = await session_store.get_session(session_id)
        assert session is not None
        _assert_grounded(second, session.turns[-1].evidence_bundle)
        content = " ".join(
            (second.recommendation.summary,)
            + tuple(action.action for action in second.recommendation.actions)
        ).lower()
        assert any(keyword in content for keyword in ("shelter", "relief", "evacuat"))

    async def test_follow_up_narrows_focus_to_shelters_not_general_overview(
        self, provider
    ):
        orchestrator, session_store, tools = _build_orchestrator(provider)
        session_id, _ = await orchestrator.handle_turn(
            None,
            _request("What is the flood situation in Mingora?", "Mingora"),
        )
        _, second = await orchestrator.handle_turn(
            session_id,
            _request("What about shelters?", "Mingora"),
        )

        session = await session_store.get_session(session_id)
        assert session is not None
        _assert_grounded(second, session.turns[-1].evidence_bundle)
        assert second.recommendation.actions, (
            "Turn 2 must recommend at least one action to be shelter-focused."
        )
        shelter_related = _shelter_related_references(session.turns[-1].evidence_bundle)
        assert any(
            _is_shelter_grounded(action, shelter_related)
            for action in second.recommendation.actions
        ), "Turn 2 must include at least one action grounded in shelter evidence."
        assert _is_shelter_grounded(second.recommendation.actions[0], shelter_related), (
            "Turn 2's first (highest-priority) action must be shelter-grounded, "
            "proving shelters lead the response rather than appear as an "
            "afterthought."
        )

    async def test_follow_up_narrows_focus_to_policy_not_general_overview(
        self, provider
    ):
        orchestrator, session_store, tools = _build_orchestrator(provider)
        session_id, first = await orchestrator.handle_turn(
            None,
            _request("What is the flood situation in Mingora?", "Mingora"),
        )
        _, second = await orchestrator.handle_turn(
            session_id,
            _request("What about the government policy?", "Mingora"),
        )

        session = await session_store.get_session(session_id)
        assert session is not None
        _assert_grounded(second, session.turns[-1].evidence_bundle)
        assert second.recommendation.actions, (
            "Turn 2 must recommend at least one action to be policy-focused."
        )
        knowledge_reference = "PDMA Flood Preparedness Plan:p3:Shelters"
        assert knowledge_reference in _all_references(second), (
            "Turn 2 must cite the retrieved government-knowledge evidence."
        )
        assert (
            knowledge_reference in second.recommendation.actions[0].evidence_references
        ), (
            "Turn 2's first (highest-priority) action must be grounded in the "
            "retrieved government-policy evidence, proving policy content leads "
            "rather than appearing as an afterthought."
        )
        assert second.recommendation.summary != first.recommendation.summary, (
            "Turn 2 must not repeat turn 1's summary verbatim."
        )
        first_words = set(first.recommendation.summary.lower().split())
        second_words = set(second.recommendation.summary.lower().split())
        overlap = len(first_words & second_words) / max(len(second_words), 1)
        assert overlap < 0.6, (
            "Turn 2's summary overlaps too heavily with turn 1's general "
            "flood-status recap instead of substantively discussing the "
            "retrieved government policy guidance."
        )

    async def test_village_change_refreshes_evidence_without_cross_turn_leakage(
        self, provider
    ):
        orchestrator, session_store, tools = _build_orchestrator(provider)
        session_id, _ = await orchestrator.handle_turn(
            None,
            _request("What is the flood outlook for Mingora?", "Mingora"),
        )
        _, second = await orchestrator.handle_turn(
            session_id,
            _request("What is the flood outlook for Saidu Sharif?", "Saidu Sharif"),
        )

        assert all(count == 2 for count in _tool_call_counts(tools).values())
        session = await session_store.get_session(session_id)
        assert session is not None
        _assert_grounded(second, session.turns[-1].evidence_bundle)
        assert not any(
            "mingora" in reference.lower()
            for reference in _all_references(second)
        )

    async def test_consecutive_follow_ups_reuse_evidence_and_pass_two_summaries(
        self, provider
    ):
        orchestrator, session_store, tools = _build_orchestrator(provider)
        with patch.object(
            provider._prompt_builder,
            "build",
            wraps=provider._prompt_builder.build,
        ) as build:
            session_id, first = await orchestrator.handle_turn(
                None,
                _request("What is the flood outlook for Mingora?", "Mingora"),
            )
            _, second = await orchestrator.handle_turn(
                session_id,
                _request("What about shelters near there?", "Mingora"),
            )
            _, third = await orchestrator.handle_turn(
                session_id,
                _request("What evacuation actions are appropriate?", "Mingora"),
            )

        assert all(count == 1 for count in _tool_call_counts(tools).values())
        session = await session_store.get_session(session_id)
        assert session is not None
        for turn, decision in zip(session.turns, (first, second, third), strict=True):
            _assert_grounded(decision, turn.evidence_bundle)
        history = build.call_args_list[-1].kwargs["history"]
        assert [turn.recommendation_summary for turn in history] == [
            first.recommendation.summary,
            second.recommendation.summary,
        ]
