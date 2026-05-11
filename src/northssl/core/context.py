from dataclasses import dataclass

from northssl.config.settings import NorthSSLSettings

@dataclass(slots=True)
class NorthSSLContext:
    settings: NorthSSLSettings