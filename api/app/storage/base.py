from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def url(self, key: str, ttl: int) -> str:
        """A URL an <img> tag can load with no Authorization header.

        LocalStorage signs its own /media/{key} route. An S3-compatible
        backend returns a presigned URL from this same method — callers
        never need to know which.
        """
        ...
