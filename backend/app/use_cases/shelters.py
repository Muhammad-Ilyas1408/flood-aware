"""Application use case for viewing configured shelter records."""

from backend.app.dtos.datasets import ShelterListDTO
from backend.app.services.protocols import ShelterServiceProtocol


class ViewSheltersUseCase:
    """Coordinate the application task of viewing configured shelters."""

    def __init__(self, service: ShelterServiceProtocol) -> None:
        """Initialize the use case with its shelter service dependency."""

        self._service: ShelterServiceProtocol = service

    def execute(self) -> ShelterListDTO:
        """Return configured shelter records without transforming the DTO."""

        return self._service.load_shelters()
