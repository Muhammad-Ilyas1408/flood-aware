"""Canonical assembly of prepared flood context into GIS domain requests."""

from backend.app.gis.domain.exceptions import GISRequestFactoryError
from backend.app.gis.domain.models import GISDomainRequest, PreparedFloodContext


class GISRequestFactory:
    """Construct GIS requests without understanding forecast or spatial origins."""

    def build(self, context: PreparedFloodContext) -> GISDomainRequest:
        """Construct the immutable GIS request from one prepared flood context."""
        if not isinstance(context, PreparedFloodContext):
            raise GISRequestFactoryError(
                "GIS request factory requires a PreparedFloodContext."
            )
        try:
            return GISDomainRequest(context=context)
        except Exception as error:
            raise GISRequestFactoryError(
                "GIS domain request could not be assembled."
            ) from error
