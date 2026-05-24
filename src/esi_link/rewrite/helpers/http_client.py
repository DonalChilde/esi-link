"""This module provides helper functions to configure HTTP clients for making requests to the ESI API.

Using these helper functions ensures that all requests made to the ESI API include the
necessary headers, such as the User-Agent.
"""

from httpx2 import AsyncClient, Client


def config_http_client(user_agent: str) -> Client:
    """Configures the HTTP client with the provided user agent."""
    return Client(headers={"User-Agent": user_agent})


async def config_async_http_client(user_agent: str) -> AsyncClient:
    """Configures the asynchronous HTTP client with the provided user agent."""
    return AsyncClient(headers={"User-Agent": user_agent})
