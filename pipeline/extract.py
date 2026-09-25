"""Fixed-origin, size-bounded HTTPS retrieval. Redirects and compression are rejected."""

import ipaddress
import re
import socket
import time
from urllib.parse import urlsplit

import httpx

MAX_BYTES = 2_000_000


def validate_url(url: str, resolve: bool = True) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "ted.europa.eu"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"/en/notice/\d{1,6}-\d{4}/xml", parsed.path)
    ):
        raise ValueError("Source URL is outside the fixed TED XML allowlist")
    if resolve:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Source resolved to a non-public network")


def download(url: str) -> bytes:
    validate_url(url)
    for attempt in range(3):
        try:
            with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
                with client.stream(
                    "GET",
                    url,
                    headers={
                        "Accept-Encoding": "identity",
                        "User-Agent": "BGTransparencyExplorer/0.1 (bounded research import)",
                    },
                ) as response:
                    if response.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError(
                            "Retryable source failure", request=response.request, response=response
                        )
                    response.raise_for_status()
                    if response.headers.get("content-encoding", "identity") != "identity":
                        raise ValueError("Compressed source responses are not supported")
                    data = bytearray()
                    for chunk in response.iter_raw():
                        data.extend(chunk)
                        if len(data) > MAX_BYTES:
                            raise ValueError("Source response exceeds 2 MB")
                    return bytes(data)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable")
