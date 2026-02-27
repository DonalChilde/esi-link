"""Pre-defined response handlers."""

from esi_link.v2.models import EsiResponse, ResponseHandlerProtocol


class DummyResponseHandler(ResponseHandlerProtocol):
    """A dummy response handler that does nothing."""

    async def handle_response(self, response: EsiResponse) -> None:
        """Handle the response by doing nothing."""
        pass
