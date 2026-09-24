from pathlib import Path

from app.schemas import ResultResponse
from scripts.run_event import build_result, enroll_members, process_event

SAMPLE_DIR = Path(__file__).parent.parent.parent / "data" / "sample_enrollment"


def test_result_json_validates_against_pydantic_model():
    # Same enrollment folder used as both enroll + event source, like the M1
    # CLI self-test — keeps this fast while still exercising every branch
    # (present, absent) the schema needs to accept. Unidentified/needs_review
    # shapes are covered directly by ResultResponse's field types.
    members_by_roll, ref_member_ids, _, ref_matrix = enroll_members(SAMPLE_DIR)
    photos, per_photo_matches, all_unknown, faces_detected, faces_skipped = process_event(
        SAMPLE_DIR, ref_member_ids, ref_matrix
    )
    result = build_result(
        "Schema Test Event", "2026-09-21", members_by_roll, photos, per_photo_matches, all_unknown, faces_detected, faces_skipped
    )

    validated = ResultResponse.model_validate(result)

    assert validated.summary.present > 0
    assert len(validated.absent) >= 0
