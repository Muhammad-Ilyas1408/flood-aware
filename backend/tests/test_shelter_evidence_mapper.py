"""Tests for distance-based shelter relevance in ShelterEvidenceMapper.

Covers the real gap found via live testing: a village question for
Mingora reported shelter data as unavailable even though a real,
operational shelter ("Government Degree College Mingora") exists close
by in the production dataset. The root cause was that no matching logic
existed at all -- every shelter, regardless of location, was handed to
the decision agent as an anonymous name. These tests cover the new
distance/status-based relevance logic directly, plus a regression test
against the real, checked-in production dataset for this exact scenario.
"""

import unittest

from backend.app.config.datasets import create_production_dataset_catalog_config
from backend.app.data.repositories import CSVRepository
from backend.app.dtos.datasets import ShelterDTO, ShelterListDTO
from backend.app.graph.mappers.configured_data_mappers import ShelterEvidenceMapper
from backend.app.graph.state import Coordinate
from backend.app.services.services import ShelterService


class ShelterEvidenceMapperUnitTests(unittest.TestCase):
    """Synthetic unit coverage for the distance/status matching logic."""

    def test_no_origin_returns_every_shelter_unfiltered(self) -> None:
        """Without a request location, relevance cannot be computed."""
        dto = ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name="Far Shelter", district="X", capacity=10,
                    latitude=10.0, longitude=10.0,
                ),
            )
        )

        evidence = ShelterEvidenceMapper.to_graph(dto, origin=None)

        self.assertEqual(evidence.shelters, ("Far Shelter",))
        self.assertIsNone(evidence.nearest_shelter)

    def test_shelter_outside_radius_is_excluded(self) -> None:
        origin = Coordinate(latitude=34.7700, longitude=72.3600)
        dto = ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name="Distant Shelter", district="X", capacity=10,
                    latitude=35.2000, longitude=72.6000,  # ~53km away
                ),
            )
        )

        evidence = ShelterEvidenceMapper.to_graph(dto, origin=origin)

        self.assertEqual(evidence.shelters, ())
        self.assertIsNone(evidence.nearest_shelter)
        self.assertIsNone(evidence.available_capacity)

    def test_closed_shelter_is_excluded_even_when_nearest(self) -> None:
        origin = Coordinate(latitude=34.7700, longitude=72.3600)
        dto = ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name="Closed Camp", district="X", capacity=100,
                    latitude=34.7700, longitude=72.3600, status="Closed",
                ),
                ShelterDTO(
                    name="Open School", district="X", capacity=200,
                    latitude=34.7720, longitude=72.3620, status="Operational",
                ),
            )
        )

        evidence = ShelterEvidenceMapper.to_graph(dto, origin=origin)

        self.assertNotIn("Closed Camp", evidence.shelters)
        self.assertEqual(evidence.nearest_shelter, "Open School")
        self.assertEqual(evidence.available_capacity, 200)

    def test_nearest_shelter_is_the_closest_operational_one(self) -> None:
        origin = Coordinate(latitude=0.0, longitude=0.0)
        dto = ShelterListDTO(
            shelters=(
                ShelterDTO(
                    name="Closer", district="X", capacity=50,
                    latitude=0.01, longitude=0.01,
                ),
                ShelterDTO(
                    name="Farther", district="X", capacity=99,
                    latitude=0.03, longitude=0.03,
                ),
            )
        )

        evidence = ShelterEvidenceMapper.to_graph(dto, origin=origin)

        self.assertEqual(evidence.nearest_shelter, "Closer")
        self.assertEqual(evidence.available_capacity, 50)
        self.assertEqual(evidence.shelters, ("Closer", "Farther"))


class MingoraRealDataRegressionTest(unittest.TestCase):
    """Regression test for the exact live-testing-confirmed bug report.

    Reproduces asking about shelters for village_name="Mingora" using
    Mingora's real coordinates against the real, checked-in
    data/datasets/shelters.csv -- not a fixture -- and asserts the real
    "Government Degree College Mingora" shelter is now found.
    """

    MINGORA_COORDINATES = Coordinate(latitude=34.7700, longitude=72.3600)

    @classmethod
    def setUpClass(cls) -> None:
        config = create_production_dataset_catalog_config()
        repository = CSVRepository(config.shelters)
        cls.shelters_dto = ShelterService(repository).load_shelters()

    def test_government_degree_college_mingora_is_found_and_grounded(self) -> None:
        evidence = ShelterEvidenceMapper.to_graph(
            self.shelters_dto, origin=self.MINGORA_COORDINATES
        )

        self.assertIn("Government Degree College Mingora", evidence.shelters)
        self.assertIsNotNone(evidence.nearest_shelter)
        self.assertIsNotNone(evidence.available_capacity)

    def test_2009_closed_relief_camps_are_not_recommended(self) -> None:
        """Several 2009-era relief camps sit at ~0km but are long closed."""
        evidence = ShelterEvidenceMapper.to_graph(
            self.shelters_dto, origin=self.MINGORA_COORDINATES
        )

        self.assertNotIn("Relief Camp Jail Road Mingora", evidence.shelters)
        self.assertNotIn("Relief Camp Regal Chowk Mingora", evidence.shelters)

    def test_distant_tehsils_are_not_recommended(self) -> None:
        evidence = ShelterEvidenceMapper.to_graph(
            self.shelters_dto, origin=self.MINGORA_COORDINATES
        )

        self.assertNotIn("Govt High School Bahrain", evidence.shelters)
        self.assertNotIn("Govt Degree College Khwazakhela", evidence.shelters)

    def test_shelter_evidence_is_no_longer_entirely_absent(self) -> None:
        """The exact reported symptom: shelter evidence must not come back empty."""
        evidence = ShelterEvidenceMapper.to_graph(
            self.shelters_dto, origin=self.MINGORA_COORDINATES
        )

        self.assertTrue(evidence.shelters, "Mingora must resolve at least one shelter.")


if __name__ == "__main__":
    unittest.main()
