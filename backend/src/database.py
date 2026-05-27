from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.modules.identity.infrastructure.config import AuthSettings


def _get_sync_database_url() -> str:
    settings = AuthSettings()
    database_url = settings.database_url
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("+asyncpg", "", 1)
    return database_url


engine = create_engine(_get_sync_database_url(), echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
