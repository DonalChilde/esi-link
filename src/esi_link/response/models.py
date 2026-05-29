"""Models to support the various Response objects returned by the ESI Link API."""

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseData:
    """Represents the data returned in a successful response to an ESI request.

    This is a generic model that can be extended to include specific fields for different types of responses.
    """

    pass


@dataclass(slots=True, kw_only=True, frozen=True)
class ResponseDebug:
    """Represents debug information included in the response to an ESI request.

    This can include details about the request processing, such as validation results, execution time, etc.
    """

    pass
