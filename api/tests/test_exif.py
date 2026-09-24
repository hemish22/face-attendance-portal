from pathlib import Path

from PIL import Image, ImageOps

from core.detect import detect_faces
from scripts.run_event import load_exif_corrected_bgr

SAMPLE = Path(__file__).parent.parent.parent / "data" / "sample_enrollment" / "hemish_jain.jpg"


def test_exif_rotated_image_gives_upright_bbox(tmp_path):
    baseline_image = load_exif_corrected_bgr(SAMPLE)
    baseline_faces = [f for f in detect_faces(baseline_image) if not f.skipped]
    assert len(baseline_faces) == 1
    bh, bw = baseline_image.shape[:2]
    baseline_center = (
        (baseline_faces[0].bbox[0] + baseline_faces[0].bbox[2]) / 2 / bw,
        (baseline_faces[0].bbox[1] + baseline_faces[0].bbox[3]) / 2 / bh,
    )

    # Simulate a phone that stored the sensor's raw (rotated) pixels plus an
    # EXIF orientation tag telling viewers how to correct it, as real phone
    # photos commonly do.
    im = Image.open(SAMPLE).convert("RGB")
    physically_rotated = im.rotate(90, expand=True)  # raw sensor orientation
    exif = physically_rotated.getexif()
    exif[274] = 6  # Orientation: viewer must rotate 90 CW to display correctly
    rotated_path = tmp_path / "rotated.jpg"
    physically_rotated.save(rotated_path, exif=exif)

    # Sanity: without EXIF correction the file is sideways (dimensions swapped).
    raw = Image.open(rotated_path)
    assert raw.size == (im.size[1], im.size[0])

    corrected = ImageOps.exif_transpose(raw)
    assert corrected.size == im.size  # back to the original upright dimensions

    corrected_image = load_exif_corrected_bgr(rotated_path)
    ch, cw = corrected_image.shape[:2]
    assert (cw, ch) == im.size

    faces = [f for f in detect_faces(corrected_image) if not f.skipped]
    assert len(faces) == 1, "face should be detected upright after EXIF correction"

    center = (
        (faces[0].bbox[0] + faces[0].bbox[2]) / 2 / cw,
        (faces[0].bbox[1] + faces[0].bbox[3]) / 2 / ch,
    )
    assert abs(center[0] - baseline_center[0]) < 0.05
    assert abs(center[1] - baseline_center[1]) < 0.05
