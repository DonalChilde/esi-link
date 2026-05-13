from esi_link.simplified_models import Request, RequestGroup,ValidatedRequest,ValidatedRequestGroup


def validate_request(request: Request) -> ValidatedRequest:
    ...
def validate_request_group(request_group: RequestGroup) -> ValidatedRequestGroup:
    ...