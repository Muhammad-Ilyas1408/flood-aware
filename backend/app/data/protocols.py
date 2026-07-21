"""Structural repository contracts for future Flood-Aware data sources."""

from collections.abc import Sequence
from typing import Protocol, TypeVar

from backend.app.data.models import DatasetMetadata


_ReadItemT = TypeVar("_ReadItemT", covariant=True)
_WriteItemT = TypeVar("_WriteItemT")


class RepositoryProtocol(Protocol[_ReadItemT]):
    """Define behavior shared by all dataset repositories.

    Implementations provide metadata and validate their own readiness without
    exposing storage, transport, or format-specific details to callers.
    """

    def metadata(self) -> DatasetMetadata:
        """Return immutable metadata describing the repository dataset."""

        ...

    def validate(self) -> None:
        """Validate that the repository is ready to serve its dataset contract."""

        ...


class ReadOnlyRepositoryProtocol(RepositoryProtocol[_ReadItemT], Protocol):
    """Define read-only access to repository items."""

    def get(self, identifier: str) -> _ReadItemT:
        """Return the item identified by the supplied stable identifier."""

        ...

    def list(self) -> Sequence[_ReadItemT]:
        """Return all repository items in implementation-defined stable order."""

        ...

    def exists(self, identifier: str) -> bool:
        """Return whether an item exists for the supplied stable identifier."""

        ...

    def count(self) -> int:
        """Return the number of items available through the repository."""

        ...


class WritableRepositoryProtocol(ReadOnlyRepositoryProtocol[_WriteItemT], Protocol):
    """Define repository access that additionally permits item mutation."""

    def create(self, item: _WriteItemT) -> _WriteItemT:
        """Persist a new item and return its stored representation."""

        ...

    def update(self, identifier: str, item: _WriteItemT) -> _WriteItemT:
        """Replace an identified item and return its stored representation."""

        ...

    def delete(self, identifier: str) -> None:
        """Remove the item identified by the supplied stable identifier."""

        ...
