from whenever import Instant

from esi_link.v3.models_and_protocols import CachedResponse


def is_stale(cached_response: CachedResponse, local_max_age_seconds: int) -> bool:
    """Check if a cached response is stale based on its age."""
    now = Instant.now()
    # Local expiration check based on the time the response was cached and the local max age
    if cached_response.cached_at.add(seconds=local_max_age_seconds) < now:
        return True
    if cached_response.expires_at is None:
        return True
    if cached_response.expires_at < now:
        return True
    return False
