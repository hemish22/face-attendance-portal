import hashlib
import hmac
import time

from app.config import settings


def sign(key: str, exp: int) -> str:
    msg = f"{key}:{exp}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def make_signed_path(key: str, ttl: int) -> str:
    exp = int(time.time()) + ttl
    sig = sign(key, exp)
    return f"/media/{key}?exp={exp}&sig={sig}"


def verify(key: str, exp: int, sig: str) -> bool:
    if time.time() > exp:
        return False
    expected = sign(key, exp)
    return hmac.compare_digest(expected, sig)
