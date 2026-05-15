from esi_link.simplified_models import (
    FailedRequestValidation,
    Request,
    RequestGroup,
    ValidatedRequest,
    ValidatedRequestGroup,
)


def validate_request(
    request: Request,
) -> ValidatedRequest | FailedRequestValidation: ...
def validate_request_group(request_group: RequestGroup) -> ValidatedRequestGroup: ...
