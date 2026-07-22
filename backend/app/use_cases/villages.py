"""Application use case for viewing configured village records."""

from backend.app.dtos.datasets import VillageListDTO
from backend.app.services.protocols import VillageServiceProtocol


class ViewVillagesUseCase:
    """Coordinate the application task of viewing configured villages."""

    def __init__(self, service: VillageServiceProtocol) -> None:
        """Initialize the use case with its village service dependency."""

        self._service: VillageServiceProtocol = service

    def execute(self) -> VillageListDTO:
        """Return configured village records without transforming the DTO."""

        return self._service.load_villages()
