from functools import lru_cache

from landrag.core.config import Settings, get_settings


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()
