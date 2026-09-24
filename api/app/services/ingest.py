"""Ingest rules applied to every uploaded image, per build-spec §6."""

import io

import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

MAX_LONG_SIDE = 4000
THUMB_SIZE = 800
JPEG_QUALITY = 90


def ingest_image(raw: bytes) -> tuple[bytes, bytes, int, int]:
    """Returns (stored_jpeg_bytes, thumb_jpeg_bytes, width, height)."""
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image)  # must happen before anything else
    image = image.convert("RGB")

    long_side = max(image.width, image.height)
    if long_side > MAX_LONG_SIDE:
        scale = MAX_LONG_SIDE / long_side
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)

    stored_buf = io.BytesIO()
    image.save(stored_buf, format="JPEG", quality=JPEG_QUALITY)

    thumb = image.copy()
    thumb.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb.save(thumb_buf, format="JPEG", quality=JPEG_QUALITY)

    return stored_buf.getvalue(), thumb_buf.getvalue(), image.width, image.height
