"""Integration tests for the /villages/summary API endpoint.

These tests inject a fake use case through FastAPI's standard
``app.dependency_overrides`` mechanism, so they never construct the real
graph/weather/forecast composition root and never make real OpenWeatherMap
or GloFAS calls.
"""

import asyncio
import json
import unittest
from datetime import UTC, datetime

from fastapi import FastAPI

from backend.app.config.graph_dependencies import get_village_summary_use_case
from backend.app.dtos.village_summary import VillageSummaryResultDTO
from backend.app.main import create_application
from backend.app.models.enums import FloodSeverity
from backend.app.village_summary.models import VillageConditionSummary, WeatherSnapshot


def _summary(name: str) -> VillageConditionSummary:
    """Create one complete, deterministic village condition summary."""
    return VillageConditionSummary(
        name=name,
        district="Swat",
        latitude=34.75,
        longitude=72.35,
        weather=WeatherSnapshot(
            temperature=28.5,
            weather_condition="Rain",
            weather_description="moderate rain",
            humidity=60,
            rainfall=3.0,
            observed_at=datetime(2026, 7, 27, tzinfo=UTC),
        ),
        weather_unavailable_reason=None,
        severity=FloodSeverity.MODERATE,
        severity_unavailable_reason=None,
        forecast_stale=False,
        status_message="Stay alert, monitor forecasts",
    )


class _FakeUseCase:
    """Return a scripted village-summary result while recording each request."""

    def __init__(self, result: VillageSummaryResultDTO) -> None:
        self.result = result
        self.calls: list[tuple[str, ...]] = []

    def execute(self, village_names: tuple[str, ...]) -> VillageSummaryResultDTO:
        """Record the requested names and return the configured result."""
        self.calls.append(village_names)
        return self.result


async def _get_application_response(
    application: FastAPI, path: str
) -> tuple[int, bytes]:
    """Execute a GET request against the ASGI application."""

    base_path, _, query_string = path.partition("?")
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        """Provide an empty GET request body."""

        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        """Collect ASGI response messages emitted by the application."""

        messages.append(message)

    await application(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": base_path,
            "raw_path": base_path.encode("ascii"),
            "query_string": query_string.encode("ascii"),
            "headers": [(b"accept", b"application/json")],
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


class VillageSummaryEndpointTests(unittest.TestCase):
    """Verify the endpoint coordinates the use case and schemas correctly."""

    def setUp(self) -> None:
        """Create an application whose graph dependencies are never configured."""

        self.application = create_application()

    def tearDown(self) -> None:
        """Remove dependency overrides so each test starts isolated."""

        self.application.dependency_overrides.clear()

    def test_get_village_summaries_returns_requested_villages(self) -> None:
        """A successful call returns real-shaped data for every known village."""

        use_case = _FakeUseCase(
            VillageSummaryResultDTO(
                summaries=(_summary("Bishbanr"), _summary("Kas")),
                unknown_village_names=(),
            )
        )
        self.application.dependency_overrides[get_village_summary_use_case] = (
            lambda: use_case
        )

        status_code, body = asyncio.run(
            _get_application_response(
                self.application, "/villages/summary?names=Bishbanr&names=Kas"
            )
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["data"]), 2)
        self.assertEqual(payload["data"][0]["name"], "Bishbanr")
        self.assertEqual(payload["data"][0]["severity"], "moderate")
        self.assertEqual(
            payload["data"][0]["status_message"], "Stay alert, monitor forecasts"
        )
        self.assertEqual(payload["data"][0]["weather"]["temperature"], 28.5)
        self.assertEqual(payload["unknown_village_names"], [])
        self.assertEqual(use_case.calls, [("Bishbanr", "Kas")])

    def test_get_village_summaries_reports_unknown_names_with_200(self) -> None:
        """A mix of valid and invalid names still succeeds, reporting unknowns."""

        use_case = _FakeUseCase(
            VillageSummaryResultDTO(
                summaries=(_summary("Bishbanr"),),
                unknown_village_names=("NotARealVillage",),
            )
        )
        self.application.dependency_overrides[get_village_summary_use_case] = (
            lambda: use_case
        )

        status_code, body = asyncio.run(
            _get_application_response(
                self.application,
                "/villages/summary?names=Bishbanr&names=NotARealVillage",
            )
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["unknown_village_names"], ["NotARealVillage"])

    def test_get_village_summaries_reports_only_unknown_names_with_200(self) -> None:
        """A request naming only unrecognized villages still returns 200, not 404."""

        use_case = _FakeUseCase(
            VillageSummaryResultDTO(
                summaries=(), unknown_village_names=("Nowhere",)
            )
        )
        self.application.dependency_overrides[get_village_summary_use_case] = (
            lambda: use_case
        )

        status_code, body = asyncio.run(
            _get_application_response(self.application, "/villages/summary?names=Nowhere")
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)
        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["unknown_village_names"], ["Nowhere"])

    def test_get_village_summaries_requires_at_least_one_name(self) -> None:
        """Omitting the required names parameter is rejected before the use case runs."""

        use_case = _FakeUseCase(
            VillageSummaryResultDTO(summaries=(), unknown_village_names=())
        )
        self.application.dependency_overrides[get_village_summary_use_case] = (
            lambda: use_case
        )

        status_code, _ = asyncio.run(
            _get_application_response(self.application, "/villages/summary")
        )

        self.assertEqual(status_code, 422)
        self.assertEqual(use_case.calls, [])

    def test_get_village_summaries_exposes_partial_data_honesty(self) -> None:
        """A village with unavailable severity still returns weather, and vice versa."""

        partial = VillageConditionSummary(
            name="Kozqila",
            district="Swat",
            latitude=34.73,
            longitude=72.33,
            weather=_summary("Kozqila").weather,
            weather_unavailable_reason=None,
            severity=None,
            severity_unavailable_reason=(
                "No local flood forecast is available for this location."
            ),
            forecast_stale=None,
            status_message="Insufficient data to assess flood risk",
        )
        use_case = _FakeUseCase(
            VillageSummaryResultDTO(summaries=(partial,), unknown_village_names=())
        )
        self.application.dependency_overrides[get_village_summary_use_case] = (
            lambda: use_case
        )

        status_code, body = asyncio.run(
            _get_application_response(
                self.application, "/villages/summary?names=Kozqila"
            )
        )

        self.assertEqual(status_code, 200)
        payload = json.loads(body)["data"][0]
        self.assertIsNotNone(payload["weather"])
        self.assertIsNone(payload["severity"])
        self.assertEqual(
            payload["severity_unavailable_reason"],
            "No local flood forecast is available for this location.",
        )
        self.assertEqual(
            payload["status_message"], "Insufficient data to assess flood risk"
        )


if __name__ == "__main__":
    unittest.main()
