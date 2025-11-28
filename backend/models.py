from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any


class ServerCreate(BaseModel):
    name: Optional[str] = None
    type: str = Field(..., pattern='^(http|nginx|squid|proxy)$')
    host: str
    port: Optional[int] = None
    scheme: Optional[str] = Field(None, pattern='^(http|https)$')
    path: Optional[str] = None
    interval: Optional[int] = 60

    @validator('port', pre=True, always=True)
    def default_port(cls, v, values):
        if v is None:
            if values.get('type') in ('squid', 'proxy'):
                return 3128
            return 80
        return int(v)

    @validator('scheme', pre=True, always=True)
    def default_scheme(cls, v, values):
        # infer https if port is 443, otherwise default to http
        if v is None:
            port = values.get('port')
            if port == 443:
                return 'https'
            return 'http'
        return v


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    scheme: Optional[str] = Field(None, pattern='^(http|https)$')
    path: Optional[str] = None
    interval: Optional[int] = None


class ServerOut(BaseModel):
    id: int
    name: Optional[str]
    type: str
    host: str
    port: int
    scheme: Optional[str]
    path: Optional[str]
    interval: int


class PingOut(BaseModel):
    id: int
    server_id: int
    ts: float
    ok: int
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]
    headers: Optional[Dict[str, Any]]
