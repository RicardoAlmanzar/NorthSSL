from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

def create_sqlite_engine(database_path: str | Path) -> Engine:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path.as_posix()}", future=True)
