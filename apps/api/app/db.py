# apps/api/app/db.py
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .settings import settings

_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


def _init_engine() -> None:
    """
    IMPORTANT:
    - Do NOT create the engine at import time.
    - This keeps unit tests (fuzz/regression) from requiring DATABASE_URL.
    """
    global _engine, _session_factory
    if _engine is not None:
        return

    if not settings.DATABASE_URL:
        # Let import succeed; raise only when someone actually tries to use DB.
        return

    _engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
    _session_factory = sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_engine() -> AsyncEngine:
    _init_engine()
    if _engine is None:
        raise RuntimeError("DATABASE_URL is not set (or invalid); cannot create DB engine.")
    return _engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _init_engine()
    if _session_factory is None:
        raise RuntimeError("DATABASE_URL is not set (or invalid); cannot create DB session.")
    async with _session_factory() as session:
        yield session
