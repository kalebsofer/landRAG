from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from landrag.core.config import get_settings


def get_async_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=settings.app_env == "development")


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = get_async_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sync_engine():
    settings = get_settings()
    return create_engine(settings.database_url_sync, echo=settings.app_env == "development")


def get_sync_session_factory() -> sessionmaker:
    engine = get_sync_engine()
    return sessionmaker(engine)
