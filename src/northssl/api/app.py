from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from northssl.api.errors import install_exception_handlers
from northssl.api.routers.certificates import router as certificates_router
from northssl.api.routers.health import router as health_router
from northssl.api.routers.logs import router as logs_router
from northssl.api.routers.nginx import router as nginx_router
from northssl.api.routers.renewal import router as renewal_router
from northssl.api.routers.system import router as system_router
from northssl.config.settings import NorthSSLSettings
from northssl.utils.logging import configure_logging


def create_app(settings: NorthSSLSettings | None = None) -> FastAPI:
    settings = settings or NorthSSLSettings()
    configure_logging(settings.log_level, settings.log_file_path)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="NorthSSL API for discovery, certificate management, and dashboard consumption.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(certificates_router)
    app.include_router(system_router)
    app.include_router(logs_router)
    app.include_router(nginx_router)
    app.include_router(renewal_router)

    @app.get("/status", include_in_schema=False)
    def legacy_status() -> dict[str, object]:
        services = getattr(app.state, "services", None)
        if services is None:
            return {"status": "ok"}
        diagnostics = services.discovery_service.collect()
        return {
            "settings": services.settings.model_dump(mode="json"),
            "diagnostics": asdict(diagnostics),
        }

    @app.on_event("startup")
    def startup() -> None:
        app.state.services = None

    @app.on_event("startup")
    def warm_services() -> None:
        from northssl.api.dependencies import get_api_services

        app.state.services = get_api_services()

    return app
