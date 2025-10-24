from whenever import Instant

from esi_link.helpers.download_file import download_json
from esi_link.helpers.resolve_json_ref import resolve_internal_refs
from esi_link.models import EsiLinkError, EsiSchema


def download_esi_schema(url: str, headers: dict[str, str]) -> EsiSchema:
    """Download the ESI schema from the specified URL.

    Also resolves internal JSON references.

    Args:
        url: The URL to download the schema from.
        headers: Headers to include in the request.

    Returns:
        An EsiSchema instance representing the downloaded schema.
    """
    try:
        response = download_json(url, headers=headers)
        resolved_schema = resolve_internal_refs(response, response)
        if resolved_schema.get("openapi") is None:
            raise EsiLinkError("Downloaded schema is not a valid OpenAPI schema.")
        return EsiSchema.from_schema(
            schema=resolved_schema, download_date=Instant.now()
        )
    except Exception as e:
        raise EsiLinkError(f"Failed to download schema: {e}") from e
