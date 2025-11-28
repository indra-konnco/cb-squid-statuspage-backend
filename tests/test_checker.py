import pytest

import asyncio

from backend import checker


def test_sanitize_host_port_defaults():
    h, p = checker.sanitize_host_port('example.com', None)
    assert h == 'example.com'
    assert p == 80


def test_unknown_type():
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(checker.check('unknown', 'localhost', 1234))
    assert res['ok'] is False
    assert 'unknown target type' in res['error']


class DummyResp:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


class DummyClient:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        return self._resp


def test_check_http_server_monkeypatch(monkeypatch):
    resp = DummyResp(200, {"server": "nginx"})
    monkeypatch.setattr('httpx.AsyncClient', lambda *args, **kwargs: DummyClient(resp))

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(checker.check('http', 'example.com', 80, '/'))
    assert res['ok'] is True
    assert res['status_code'] == 200
