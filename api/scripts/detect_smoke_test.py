"""M0 done-check: prints boxes and 512-d embeddings for a test image.

Usage: python -m scripts.detect_smoke_test <image_path>
"""

import sys

import cv2
from PIL import Image, ImageOps

from core.detect import detect_faces


def load_exif_corrected_bgr(path: str):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    return cv2.cvtColor(__import__("numpy").array(img), cv2.COLOR_RGB2BGR)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "../data/sample_enrollment/hemish_jain.jpg"
    image = load_exif_corrected_bgr(path)
    faces = detect_faces(image)

    print(f"{path}: {len(faces)} face(s) found, image size {image.shape[1]}x{image.shape[0]}")
    for i, f in enumerate(faces):
        status = f"SKIPPED ({f.skip_reason})" if f.skipped else "ok"
        print(f"  face {i}: bbox={f.bbox.round(1).tolist()} det_score={f.det_score:.3f} "
              f"embedding_dim={f.embedding.shape[0]} status={status}")


if __name__ == "__main__":
    main()
