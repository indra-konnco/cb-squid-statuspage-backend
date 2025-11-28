import asyncio
import time
from typing import Optional, Dict, Any
import os

import httpx


# Default test URL for Squid checks (can be overridden via SQUID_HTTP_TARGET env var)
SQUID_HTTP_TARGET = os.getenv('SQUID_HTTP_TARGET', 'https://httpbin.org/get')


async def check_http_server(host: str, port: int = 80, scheme: str = 'http', path: str = '/', timeout: float = 5.0) -> Dict[str, Any]:
    url = f"{scheme}://{host}:{port}{path}"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
        elapsed = (time.monotonic() - start) * 1000.0
        return {
            'ok': True,
            'type': 'http',
            'url': url,
            'status_code': resp.status_code,
            'latency_ms': round(elapsed, 1),
            'headers': dict(resp.headers),
        }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000.0
        return {'ok': False, 'type': 'http', 'url': url, 'error': str(e), 'latency_ms': round(elapsed, 1)}


async def check_squid_proxy(host: str, port: int = 3128, test_url: Optional[str] = None, timeout: float = 8.0) -> Dict[str, Any]:
    """
    Check a Squid proxy by sending an HTTP request through the proxy to `test_url`.
    If test_url is not provided, uses SQUID_HTTP_TARGET env var (default: https://httpbin.org/get).

    Returns a dict with success flag, HTTP status, latency, and any error.
    """
    if test_url is None:
        test_url = SQUID_HTTP_TARGET
    proxy = f'http://{host}:{port}'
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(proxies={"http://": proxy, "https://": proxy}, timeout=timeout) as client:
            resp = await client.get(test_url)
        elapsed = (time.monotonic() - start) * 1000.0
        return {
            'ok': True,
            'type': 'squid',
            'proxy': proxy,
            'test_url': test_url,
            'status_code': resp.status_code,
            'latency_ms': round(elapsed, 1),
            'headers': dict(resp.headers),
        }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000.0
        return {'ok': False, 'type': 'squid', 'proxy': proxy, 'test_url': test_url, 'error': str(e), 'latency_ms': round(elapsed, 1)}


def sanitize_host_port(host: str, port: Optional[int]) -> (str, int):
    if port is None:
        port = 80
    return host, int(port)


async def check(target_type: str, host: str, port: Optional[int] = None, scheme: str = 'http', path: str = '/', timeout: float = 8.0, test_url: Optional[str] = None) -> Dict[str, Any]:
    host, port = sanitize_host_port(host, port)
    if target_type.lower() in ('http', 'nginx'):
        return await check_http_server(host, port, scheme, path, timeout)
    if target_type.lower() in ('squid', 'proxy'):
        return await check_squid_proxy(host, port or 3128, test_url or None, timeout)
    return {'ok': False, 'error': f'unknown target type: {target_type}'}
