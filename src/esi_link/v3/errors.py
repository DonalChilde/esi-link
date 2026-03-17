class EsiLinkError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ResponseHandlingError(EsiLinkError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidHandlerConfigError(EsiLinkError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class HandlerNotFoundError(EsiLinkError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
