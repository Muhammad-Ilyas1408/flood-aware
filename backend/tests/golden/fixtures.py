"""Reusable EvidenceBundle builders for golden-set scenarios."""

from datetime import UTC, datetime

from backend.app.graph.state import (
    EvidenceBundle,
    EvidenceConflict,
    EvidenceDuplicate,
    EvidenceObservation,
    EvidenceProvenance,
    DatasetEvidence,
    ForecastEvidence,
    GISEvidence,
    KnowledgeEvidence,
    ShelterEvidence,
    VillageEvidence,
    WeatherEvidence,
)

_NOW = datetime(2026, 7, 27, tzinfo=UTC)


def provenance(evidence_type: str, tool_name: str) -> EvidenceProvenance:
    """Build one minimal, valid provenance record."""
    return EvidenceProvenance(
        evidence_type=evidence_type, tool_name=tool_name, observed_at=_NOW
    )


def scenario_severe_forecast_gis() -> EvidenceBundle:
    """Scenario 1: high-discharge forecast + high GIS exposure, no conflicts."""
    return EvidenceBundle(
        forecast=ForecastEvidence(
            discharge=5200, severity="high", return_period="1-in-50", lead_time=24
        ),
        gis=GISEvidence(
            flood_zone="high_risk", population_exposed=18000, exposure_level="high"
        ),
        provenance=(
            provenance("forecast", "glofas_forecast_tool"),
            provenance("gis", "gis_domain_service"),
        ),
    )


def scenario_calm_baseline() -> EvidenceBundle:
    """Scenario 2: low forecast, minimal GIS exposure."""
    return EvidenceBundle(
        forecast=ForecastEvidence(discharge=400, severity="normal"),
        gis=GISEvidence(flood_zone="low_risk", population_exposed=50),
        provenance=(
            provenance("forecast", "glofas_forecast_tool"),
            provenance("gis", "gis_domain_service"),
        ),
    )


def scenario_conflicting_severity() -> EvidenceBundle:
    """Scenario 5: forecast and GIS disagree on severity."""
    return EvidenceBundle(
        forecast=ForecastEvidence(discharge=1200, severity="moderate"),
        gis=GISEvidence(flood_zone="high_risk", exposure_level="high"),
        provenance=(
            provenance("forecast", "glofas_forecast_tool"),
            provenance("gis", "gis_domain_service"),
        ),
        conflicts=(
            EvidenceConflict(
                subject="flood_severity",
                observations=(
                    EvidenceObservation(
                        evidence_type="forecast",
                        value="moderate",
                        origin=provenance("forecast", "glofas_forecast_tool"),
                    ),
                    EvidenceObservation(
                        evidence_type="gis",
                        value="high",
                        origin=provenance("gis", "gis_domain_service"),
                    ),
                ),
            ),
        ),
    )


def scenario_empty_bundle() -> EvidenceBundle:
    """Scenario 6: no meaningful evidence at all."""
    return EvidenceBundle()


def scenario_shelter_recommendation() -> EvidenceBundle:
    """Moderate flood evidence with one affected village and shelter."""
    return EvidenceBundle(
        forecast=ForecastEvidence(discharge=1400, severity="moderate"),
        villages=(VillageEvidence(village_name="Banda Daud Shah", population=2400),),
        shelters=ShelterEvidence(shelters=("Al-Noor Community Shelter",)),
        provenance=(
            provenance("forecast", "glofas_forecast_tool"),
            provenance("village", "village_tool"),
            provenance("shelter", "shelter_tool"),
        ),
    )


def scenario_knowledge_only() -> EvidenceBundle:
    """Policy-only evidence without forecast or GIS facts."""
    citations = ("PDMA Flood Contingency Plan 2025", "PDMA Shelter Protocol 2024")
    return EvidenceBundle(
        knowledge=KnowledgeEvidence(citations=citations),
        provenance=(provenance("knowledge", "government_knowledge_tool"),),
    )


def scenario_extreme_exposure() -> EvidenceBundle:
    """High discharge with severe population and infrastructure exposure."""
    return EvidenceBundle(
        forecast=ForecastEvidence(discharge=8500, severity="extreme"),
        gis=GISEvidence(
            flood_zone="extreme_risk", population_exposed=250000,
            infrastructure_exposed=900, exposure_level="extreme",
        ),
        provenance=(
            provenance("forecast", "glofas_forecast_tool"),
            provenance("gis", "gis_domain_service"),
        ),
    )


def scenario_weather_only() -> EvidenceBundle:
    """Heavy observed rainfall without hydrological forecast evidence."""
    return EvidenceBundle(
        weather=WeatherEvidence(rainfall=220, weather_condition="heavy_rain"),
        provenance=(provenance("weather", "weather_tool"),),
    )


def scenario_multiple_villages() -> EvidenceBundle:
    """Three exposed villages requiring locality-specific evidence references."""
    return EvidenceBundle(
        villages=(
            VillageEvidence(village_name="Kot Addu", population=5100),
            VillageEvidence(village_name="Jhang", population=3800),
            VillageEvidence(village_name="Charsadda", population=7200),
        ),
        provenance=(provenance("village", "village_tool"),),
    )


def scenario_capacity_shortfall() -> EvidenceBundle:
    """Shelter capacity is materially lower than exposed population."""
    return EvidenceBundle(
        gis=GISEvidence(population_exposed=18000, flood_zone="high_risk"),
        shelters=ShelterEvidence(
            shelters=("Dera Relief Centre",), available_capacity=120
        ),
        provenance=(
            provenance("gis", "gis_domain_service"),
            provenance("shelter", "shelter_tool"),
        ),
    )


def scenario_duplicate_evidence() -> EvidenceBundle:
    """Severe forecast and GIS evidence containing one retained duplicate."""
    base = scenario_severe_forecast_gis()
    forecast_origin = provenance("forecast", "glofas_forecast_tool")
    return base.model_copy(
        update={
            "duplicates": (
                EvidenceDuplicate(
                    reference="glofas_forecast_tool",
                    origins=(forecast_origin, forecast_origin),
                ),
            )
        }
    )


def scenario_full_bundle() -> EvidenceBundle:
    """Complete multi-source evidence for broad citation coverage."""
    return EvidenceBundle(
        weather=WeatherEvidence(rainfall=95, weather_condition="rain"),
        forecast=ForecastEvidence(discharge=3300, severity="high"),
        gis=GISEvidence(flood_zone="high_risk", population_exposed=22000),
        villages=(VillageEvidence(village_name="Nowshera", population=8400),),
        shelters=ShelterEvidence(shelters=("Nowshera Relief Camp",), available_capacity=900),
        knowledge=KnowledgeEvidence(citations=("PDMA Response Framework 2025",)),
        datasets=DatasetEvidence(datasets=("GloFAS Control Forecast",)),
        provenance=tuple(provenance(kind, f"{kind}_tool") for kind in (
            "weather", "forecast", "gis", "village", "shelter", "knowledge", "dataset"
        )),
    )
