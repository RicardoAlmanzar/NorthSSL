from northssl.config.settings import NorthSSLSettings

from .context import NorthSSLContext
from northssl.utils.logging import configure_logging

def load_settings() -> NorthSSLSettings:
    return NorthSSLSettings()

def initialize_context() -> NorthSSLContext:
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_file_path)
    return NorthSSLContext(settings=settings)
