import os
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, HttpUrl, conint
from curl_cffi.requests import BrowserTypeLiteral
from typing import get_args


BROWSER_TYPES = get_args(BrowserTypeLiteral)
API_KEY_EXPECTED = os.getenv("PROXY_API_KEY", "")
_browsers = [
    "chrome99", "chrome100", "chrome101", "chrome104", "chrome107",
    "chrome110", "chrome116", "chrome119", "chrome120", "chrome123",
    "chrome124", "chrome131", "chrome133a", "chrome136", "chrome99_android", "chrome131_android",
    "edge99", "edge101", "safari15_3",
    "safari15_3", "safari15_5", "safari17_0", "safari17_2_ios", "safari18_0", "safari18_0_ios",
    "safari18_4", "safari18_4_ios", "firefox133", "tor145"
]


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ProxyRequest(BaseModel):
    method: HTTPMethod
    url: HttpUrl
    params: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    data: Optional[Any] = None        # form / json / bytes
    cookies: Optional[Dict[str, str]] = None
    impersonate: Optional[str] = None
    proxies: Optional[Dict[str, str]] = None
    timeout_ms: Optional[conint(ge=100, le=120_000)] = 10_000  # 默认10s
    return_data: bool = True
    stream: bool = False                 # 是否返回二进制
    apikey: Optional[str] = None
    proxy_chain: list = []            # 剩余链路（URL 列表）
