"""Simple function to download a text file from a web server."""

import asyncio
import logging
from time import perf_counter

import aiohttp

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


async def _download_text(url: str, session: aiohttp.ClientSession | None) -> str:
    logger.info(f"Downloading text from {url}")
    start = perf_counter()
    if session is None:
        session = aiohttp.ClientSession()
    async with session.get(url) as response:
        logger.debug(
            f"Received response with status {response.status} from {response.real_url}"
        )
        logger.debug(f"Response headers: {response.headers}")
        response.raise_for_status()
        text = await response.text()
        logger.info(
            f"Downloaded text from {url} in {perf_counter() - start:.2f} seconds"
        )
        return text


def download_text(url: str, session: aiohttp.ClientSession | None = None) -> str:
    """Download a text file from a URL and return its content as a string."""
    return asyncio.run(_download_text(url, session))
