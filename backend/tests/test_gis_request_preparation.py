"""Tests for configuration-driven flood preparation and GIS request assembly."""

from unittest.mock import Mock

import pytest

from backend.app.config.settings import Settings
from backend.app.flood.classification.exceptions import FloodClassificationError
from backend.app.flood.classification.policy import FloodClassificationPolicy
from backend.app.flood.classification.service import FloodClassificationService
from backend.app.forecast.models import ForecastResult
from backend.app.gis.domain.exceptions import GISRequestFactoryError, SpatialPolicyError
from backend.app.gis.domain.gis_request_factory import GISRequestFactory
from backend.app.gis.domain.models import PreparedFloodContext, SpatialPolicy
from backend.app.gis.domain.spatial_policy_service import SpatialPolicyService
from backend.app.gis.geometry import BoundingBox
from backend.app.models.enums import FloodSeverity
from backend.app.models.flood import Coordinates


def _forecast(*discharges: float) -> ForecastResult:
    """Build a structural canonical forecast double for classification tests."""
    forecast = Mock()
    forecast.__class__ = ForecastResult
    forecast.series.points = tuple(
        Mock(discharge_m3_per_second=discharge) for discharge in discharges
    )
    return forecast


@pytest.mark.parametrize(
    ("discharge", "expected"),
    (
        (0.0, FloodSeverity.MINOR),
        (250.0, FloodSeverity.MODERATE),
        (500.0, FloodSeverity.MAJOR),
        (1_000.0, FloodSeverity.EXTREME),
    ),
)
def test_configured_classification_boundaries(
    discharge: float, expected: FloodSeverity
) -> None:
    """The injected production policy should own every threshold boundary."""
    policy = FloodClassificationPolicy.from_settings(Settings())
    assert FloodClassificationService(policy).classify(_forecast(discharge)) is expected


def test_policy_reads_existing_application_settings() -> None:
    """Operational thresholds are sourced from existing Settings, not services."""
    settings = Settings(
        flood_moderate_discharge=11.0,
        flood_major_discharge=22.0,
        flood_extreme_discharge=33.0,
    )
    assert FloodClassificationPolicy.from_settings(settings).major_discharge == 22.0


def test_classification_rejects_noncanonical_forecast() -> None:
    """Flood classification remains constrained to ForecastResult ownership."""
    with pytest.raises(FloodClassificationError):
        FloodClassificationService(
            FloodClassificationPolicy.from_settings(Settings())
        ).classify(object())


def test_spatial_policy_produces_deterministic_bounds() -> None:
    """The spatial policy service is the sole owner of extent construction."""
    bounds = SpatialPolicyService(SpatialPolicy()).analysis_bounds(
        Coordinates(latitude=34.9, longitude=72.2)
    )
    assert bounds.min_latitude == pytest.approx(34.8)
    assert bounds.max_longitude == pytest.approx(72.3)


def test_spatial_policy_rejects_invalid_input() -> None:
    """Only canonical Coordinates may be used for spatial policy execution."""
    with pytest.raises(SpatialPolicyError):
        SpatialPolicyService(SpatialPolicy()).analysis_bounds(object())


def test_factory_consumes_prepared_context_without_forecast_coupling() -> None:
    """The factory should assemble only the immutable prepared context."""
    forecast = _forecast(500.0)
    context = PreparedFloodContext(
        forecast=forecast,
        severity=FloodSeverity.MAJOR,
        bounds=BoundingBox(
            min_latitude=34.8,
            min_longitude=72.1,
            max_latitude=35.0,
            max_longitude=72.3,
        ),
        coordinates=Coordinates(latitude=34.9, longitude=72.2),
    )
    request = GISRequestFactory().build(context)
    assert request.context is context


def test_factory_rejects_nonprepared_context() -> None:
    """GIS request assembly cannot bypass prepared flood context ownership."""
    with pytest.raises(GISRequestFactoryError):
        GISRequestFactory().build(object())
