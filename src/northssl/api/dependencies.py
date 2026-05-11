from __future__ import annotations

from functools import lru_cache

from northssl.api.services import NorthSSLApiServices, build_api_services
from northssl.core.bootstrap import load_settings


@lru_cache(maxsize=1)
def get_settings():
    return load_settings()


@lru_cache(maxsize=1)
def get_api_services() -> NorthSSLApiServices:
    return build_api_services(get_settings())
