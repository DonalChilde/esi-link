"""Simple function to download a text file from a web server."""

import asyncio
import logging
from time import perf_counter
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


async def _download_text(
    url: str, *, headers: dict[str, str], session: aiohttp.ClientSession | None
) -> str:
    """Download a text file from a URL and return its content as a string."""
    logger.info(f"Downloading text from {url}")
    start = perf_counter()
    if session is None:
        session = aiohttp.ClientSession()
    async with session.get(url, headers=headers) as response:
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


def download_text(
    url: str, *, headers: dict[str, str], session: aiohttp.ClientSession | None = None
) -> str:
    """Download a text file from a URL and return its content as a string."""
    return asyncio.run(_download_text(url, headers=headers, session=session))


async def _download_json(
    url: str, *, headers: dict[str, str], session: aiohttp.ClientSession | None
) -> Any:
    """Download a JSON file from a URL."""
    logger.info(f"Downloading JSON from {url}")
    start = perf_counter()
    if session is None:
        session = aiohttp.ClientSession()
    async with session.get(url, headers=headers) as response:
        logger.debug(
            f"Received response with status {response.status} from {response.real_url}"
        )
        logger.debug(f"Response headers: {response.headers}")
        response.raise_for_status()
        json_data = await response.json()
        logger.info(
            f"Downloaded json from {url} in {perf_counter() - start:.2f} seconds"
        )
        return json_data


def download_json(
    url: str, *, headers: dict[str, str], session: aiohttp.ClientSession | None = None
) -> Any:
    """Download a JSON file from a URL."""
    return asyncio.run(_download_json(url, headers=headers, session=session))
