"""Functions for downloading files using aiohttp.

Simple wrapper functions for downloading files, text, or JSON data from a URL using
aiohttp, with support for query parameters and headers.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
from typing import Any

import aiohttp
from multidict import CIMultiDictProxy

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


async def download_bytes_to_file(
    url: str,
    file_path: Path,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    overwrite: bool = False,
) -> CIMultiDictProxy[str]:
    """Download a file from a URL and save it to disk.

    File is first written to a temporary file, then moved to the final location to ensure atomicity.

    Args:
        url: The URL to download the file from.
        headers: The headers to include in the request.
        params: The query parameters to include in the request.
        file_path: The path to save the downloaded file to.
        overwrite: Whether to overwrite the file if it already exists.

    Returns:
        The headers from the response as a CIMultiDictProxy.
    """
    logger.info(f"Downloading file from {url}")
    if file_path.is_dir():
        logger.error(f"File path {file_path} is a directory. {url=}")
        raise IsADirectoryError(f"File path {file_path} is a directory.")
    if file_path.is_file() and not overwrite:
        logger.error(f"File {file_path} already exists and overwrite is False. {url=}")
        raise FileExistsError(
            f"File {file_path} already exists and overwrite is False."
        )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    start = perf_counter()

    async with aiohttp.ClientSession() as session:
        query_params = params if params else {}
        async with session.get(
            url, params=query_params, headers=headers, allow_redirects=True
        ) as response:
            logger.debug(
                "Received response with status %s, reason %s from %s, headers=%r",
                response.status,
                response.reason,
                response.real_url,
                response.headers,
            )
            response.raise_for_status()
            resp_headers = response.headers
            # atomic write to temp file, then move to final location
            try:
                with NamedTemporaryFile() as tmp_file:
                    tmp_file.write(await response.read())
                    tmp_file.flush()
                    shutil.copyfile(tmp_file.name, file_path)
            except Exception as e:
                logger.exception(f"Error writing file to {file_path}: {e}")
                raise e
            finally:
                try:
                    if tmp_file:  # pyright: ignore[reportPossiblyUnboundVariable]
                        tmp_file.close()
                        if os.path.exists(tmp_file.name):
                            os.remove(tmp_file.name)
                except UnboundLocalError as e:
                    logger.exception(
                        f"Temporary file was never created, tmp_file is undefined: {e}"
                    )
                    pass
                except Exception as e:
                    logger.exception(
                        f"Error cleaning up temporary file {tmp_file.name}: {e}"  # pyright: ignore[reportPossiblyUnboundVariable]
                    )

            logger.info(
                f"Downloaded and wrote file from {url} to {file_path} in {perf_counter() - start:.2f} seconds"
            )

    await asyncio.sleep(0)  # yield control to event loop
    return resp_headers


async def download_text(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[str, CIMultiDictProxy[str]]:
    """Download a text file from a URL and return its content as a string.

    Args:
        url: The URL to download the text from.
        params: The query parameters to include in the request.
        headers: The headers to include in the request.

    Returns:
        A tuple containing the downloaded text and the headers.
    """
    logger.info(f"Downloading text from {url}")
    start = perf_counter()
    async with aiohttp.ClientSession() as session:
        query_params = params if params else {}
        async with session.get(url, params=query_params, headers=headers) as response:
            logger.debug(
                "Received response with status %s, reason %s from %s, headers=%r",
                response.status,
                response.reason,
                response.real_url,
                response.headers,
            )
            response.raise_for_status()
            text = await response.text()
            logger.info(
                f"Downloaded text from {url} in {perf_counter() - start:.2f} seconds"
            )
            resp_headers = response.headers

    await asyncio.sleep(0)  # yield control to event loop
    return (text, resp_headers)


async def download_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[Any, CIMultiDictProxy[str]]:
    """Download JSON data from a URL.

    Args:
        url: The URL to download the JSON from.
        params: The query parameters to include in the request.
        headers: The headers to include in the request.

    Returns:
        A tuple containing the downloaded JSON data and the headers.
    """
    logger.info(f"Downloading JSON from {url}")
    start = perf_counter()
    async with aiohttp.ClientSession() as session:
        query_params = params if params else {}
        async with session.get(url, params=query_params, headers=headers) as response:
            logger.debug(
                "Received response with status %s, reason %s from %s, headers=%r",
                response.status,
                response.reason,
                response.real_url,
                response.headers,
            )
            response.raise_for_status()
            json_data = await response.json()
            logger.info(
                f"Downloaded json from {url} in {perf_counter() - start:.2f} seconds"
            )
            resp_headers = response.headers
    await asyncio.sleep(0)  # yield control to event loop
    return (json_data, resp_headers)
