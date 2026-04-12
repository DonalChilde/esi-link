"""ESI Authentication Library for EVE Online.

A simple library for managing EVE Online ESI authentication tokens.
"""

__app_name__ = "esi-auth"
__version__ = "0.4.0"
__author__ = "Chad Lowe"
__author_email__ = "pfmsoft.dev@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/DonalChilde/esi-auth"
__description__ = "A simple library for managing EVE Online ESI authentication tokens."

# FIXME implement esi-auth refactor to use:
# - settings mangement eg argus and eve-static-data
# - move constants to this module
OAUTH_METADATA_URL = (
    "https://login.eveonline.com/.well-known/oauth-authorization-server"
)
"""URL to fetch OAuth metadata from the ESI auth server."""
AUDIENCE = "EVE Online"
"""The audience to use for ESI Auth tokens."""
ISSUER = "https://login.eveonline.com"
"""The issuer to use for ESI Auth tokens."""
