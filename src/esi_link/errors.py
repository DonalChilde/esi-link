class EsiLinkError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class RequestValidationError(EsiLinkError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
