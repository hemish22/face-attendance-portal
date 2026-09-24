from functools import lru_cache

from app.config import settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorage(settings.STORAGE_ROOT)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
