"""HTTP/SOCKS 代理解析（账号级 IP 隔离）。"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def mask_proxy_url(url: str) -> str:
    if not url:
        return "(直连)"
    try:
        p = urlparse(url.strip())
        host = p.hostname or "?"
        port = f":{p.port}" if p.port else ""
        scheme = p.scheme or "http"
        if p.username:
            return f"{scheme}://{p.username}:***@{host}{port}"
        return f"{scheme}://{host}{port}"
    except Exception:
        return "(代理已配置)"


def build_requests_proxies(proxy_url: str | None) -> dict[str, str] | None:
    if not proxy_url or not str(proxy_url).strip():
        return None
    url = str(proxy_url).strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = f"http://{url}"
    return {"http": url, "https": url}


def resolve_account_proxy(
    proxy_url: str,
    egress_group: str,
    proxy_pools: dict[str, str],
) -> str:
    """账号 proxy_url 优先；否则用 egress_group 查 config.proxy_pools。"""
    direct = (proxy_url or "").strip()
    if direct:
        return direct
    group = (egress_group or "").strip()
    if group and proxy_pools:
        return (proxy_pools.get(group) or "").strip()
    return ""
