"""Integration tests for the conversation API endpoint.

These tests inject a fake ``ConversationOrchestrator`` through FastAPI's
standard ``app.dependency_overrides`` mechanism, so they never construct the
real graph/GIS/OpenAI composition root and never make real OpenAI or GIS
calls.
"""

import asyncio
import json
import unittest
from uuid import UUID, uuid4

from fastapi import FastAPI

from backend.app.config.graph_dependencies import get_conversation_orchestrator
from backend.app.conversation.exceptions import ConversationSessionNotFoundError
from backend.app.decision.exceptions import DecisionRateLimitedError
from backend.app.decision.models import (
    ActionRecommendation,
    Decision,
    DecisionConfidence,
    Priority,
    Recommendation,
    RiskAssessment,
    RiskLevel,
)
from backend.app.graph.state import UserRequest
from backend.app.main import create_application


def _decision() -> Decision:
    """Create a complete valid decision for deterministic API response assertions."""
    return Decision(
        risk_assessment=RiskAssessment(
            level=RiskLevel.HIGH, rationale="High discharge."
        ),
        recommendation=Recommendation(
            summary="Prepare local response.",
            actions=(
                ActionRecommendation(
                    action="Notify response teams.",
                    priority=Priority.HIGH,
                ),
            ),
            citations=("NDMA Plan:p4",),
            missing_evidence=("shelter occupancy",),
        ),
        confidence=DecisionConfidence.HIGH,
    )


class _FakeOrchestrator:
    """Return a scripted decision while recording every requested turn."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        self.default_session_id = uuid4()
        self.calls: list[tuple[UUID | None, UserRequest]] = []

    async def handle_turn(
        self, session_id: UUID | None, request: UserRequest
    ) -> tuple[UUID, Decision]:
        """Record the requested turn and return the configured decision."""
        self.calls.append((session_id, request))
        return session_id or self.default_session_id, self.decision


class _FailingOrchestrator:
    """Always raise a decision-generation failure for error-path assertions."""

    async def handle_turn(
        self, session_id: UUID | None, request: UserRequest
    ) -> tuple[UUID, Decision]:
        """Simulate a persistent provider failure instead of returning a decision."""
        del session_id, request
        raise DecisionRateLimitedError("Decision provider rate limit exceeded.")


class _UnknownSessionOrchestrator:
    """Always raise an unknown-session failure for not-found-path assertions."""

    async def handle_turn(
        self, session_id: UUID | None, request: UserRequest
    ) -> tuple[UUID, Decision]:
        """Simulate a stale or expired session id supplied by a real client."""
        del request
        raise ConversationSessionNotFoundError(
            f"Conversation session {session_id} does not exist."
        )


async def _post_application_response(
    application: FastAPI, path: str, payload: dict[str, object]
) -> tuple[int, bytes]:
    """Execute a POST request with a JSON body against the ASGI application."""

    body = json.dumps(payload).encode("utf-8")
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        """Provide the single JSON request body."""

        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        """Collect ASGI response messages emitted by the application."""

        messages.append(message)

    await application(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    status_code = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message["body"]
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(status_code), response_body


class ConversationEndpointTests(unittest.TestCase):
    """Verify the conversation endpoint coordinates the orchestrator and schemas."""

    def setUp(self) -> None:
        """Create an application whose graph dependencies are never configured."""

        self.application = create_application()

    def tearDown(self) -> None:
        """Remove dependency overrides so each test starts isolated."""

        self.application.dependency_overrides.clear()

    def test_post_conversation_returns_grounded_decision(self) -> None:
        """A successful turn returns only the minimal public decision surface."""

        orchestrator = _FakeOrchestrator(_decision())
        self.application.dependency_overrides[get_conversation_orchestrator] = (
            lambda: orchestrator
        )

        status_code, body = asyncio.run(
            _post_application_response(
                self.application,
                "/conversation",
                {
                    "request_text": "Flood outlook for Mingora?",
                    "village_name": "Mingora",
                },
            )
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["risk_level"], "high")
        self.assertEqual(payload["confidence"], "high")
        self.assertEqual(payload["summary"], "Prepare local response.")
        self.assertEqual(payload["citations"], ["NDMA Plan:p4"])
        self.assertEqual(payload["missing_evidence"], ["shelter occupancy"])
        self.assertEqual(
            payload["actions"],
            [{"action": "Notify response teams.", "priority": "high"}],
        )
        self.assertNotIn("evidence_bundle", payload)
        self.assertNotIn("reasons", payload)
        self.assertNotIn("supporting_evidence", payload)
        self.assertEqual(len(orchestrator.calls), 1)
        session_id, request = orchestrator.calls[0]
        self.assertIsNone(session_id)
        self.assertEqual(request.request_text, "Flood outlook for Mingora?")
        self.assertEqual(request.village_name, "Mingora")

    def test_post_conversation_maps_decision_generation_error_safely(self) -> None:
        """A decision-generation failure returns the centralized safe error response."""

        self.application.dependency_overrides[get_conversation_orchestrator] = (
            _FailingOrchestrator
        )

        status_code, body = asyncio.run(
            _post_application_response(
                self.application, "/conversation", {"request_text": "Flood outlook?"}
            )
        )

        self.assertEqual(status_code, 503)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(
            payload["detail"],
            "The recommendation service is temporarily unavailable. Please try again.",
        )
        self.assertNotIn("rate limit", payload["detail"].lower())

    def test_post_conversation_maps_unknown_session_to_404(self) -> None:
        """An unknown or expired session id returns a safe 404, not a server error."""

        unknown_session_id = str(uuid4())
        self.application.dependency_overrides[get_conversation_orchestrator] = (
            _UnknownSessionOrchestrator
        )

        status_code, body = asyncio.run(
            _post_application_response(
                self.application,
                "/conversation",
                {
                    "request_text": "What about shelters?",
                    "session_id": unknown_session_id,
                },
            )
        )

        self.assertEqual(status_code, 404)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(
            payload["detail"],
            "The requested conversation session was not found. "
            "Start a new conversation.",
        )
        self.assertNotIn(unknown_session_id, json.dumps(payload))
        self.assertNotIn("ConversationSessionNotFoundError", json.dumps(payload))

    def test_post_conversation_creates_session_then_reuses_supplied_id(self) -> None:
        """The first turn creates a session id; a second turn reuses the supplied one."""

        orchestrator = _FakeOrchestrator(_decision())
        self.application.dependency_overrides[get_conversation_orchestrator] = (
            lambda: orchestrator
        )

        first_status, first_body = asyncio.run(
            _post_application_response(
                self.application, "/conversation", {"request_text": "Flood outlook?"}
            )
        )
        self.assertEqual(
            first_status,
            200,
            f"First turn did not return 200, got {first_status}: {first_body!r}",
        )
        first_session_id = json.loads(first_body)["session_id"]

        second_status, second_body = asyncio.run(
            _post_application_response(
                self.application,
                "/conversation",
                {
                    "request_text": "What about shelters?",
                    "session_id": first_session_id,
                },
            )
        )
        self.assertEqual(
            second_status,
            200,
            f"Second turn did not return 200, got {second_status}: {second_body!r}",
        )
        second_session_id = json.loads(second_body)["session_id"]

        self.assertEqual(first_session_id, second_session_id)
        self.assertIsNone(orchestrator.calls[0][0])
        self.assertEqual(str(orchestrator.calls[1][0]), first_session_id)


if __name__ == "__main__":
    unittest.main()
