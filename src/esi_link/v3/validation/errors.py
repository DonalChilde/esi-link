from esi_link.v3.errors import EsiLinkError
from esi_link.v3.models import Request


class RequestValidationError(EsiLinkError):
    def __init__(self, msg: str, request: Request, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg
        self.request = request


class RequestGroupValidationError(EsiLinkError):
    def __init__(self, msg: str, request_group_id: str, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg
        self.request_group_id = request_group_id
