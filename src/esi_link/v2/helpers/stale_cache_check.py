from whenever import Instant

from esi_link.v2.models import CachedResponse


def check_stale(cached_response: CachedResponse, max_age_seconds: int) -> bool:
    """Check if a cached response is stale based on its age."""
    age = (Instant.now() - cached_response.cached_on).in_seconds()
    return age > max_age_seconds
