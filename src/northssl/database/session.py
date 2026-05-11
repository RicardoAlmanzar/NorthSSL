from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from northssl.config.settings import NorthSSLSettings
from northssl.database.models import Base


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def create_session_factory(settings: NorthSSLSettings | None = None) -> sessionmaker[Session]:
    resolved_settings = settings or NorthSSLSettings()
    resolved_settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = get_engine(resolved_settings.database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def initialize_database(settings: NorthSSLSettings | None = None) -> Engine:
    resolved_settings = settings or NorthSSLSettings()
    resolved_settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = get_engine(resolved_settings.database_url)
    Base.metadata.create_all(engine)
    return engine
