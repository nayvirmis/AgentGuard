from backend.app.domain import GroundingStatus
from backend.app.grounding import check_grounding


def test_cited_supported_claim_is_grounded():
    evidence = [
        {
            "tool_name": "document_search",
            "output": {
                "results": [
                    {
                        "source_id": "handbook_chunk_1",
                        "snippet": (
                            "Students should contact the instructor in writing "
                            "before the assignment deadline."
                        ),
                    }
                ]
            },
        }
    ]
    result = check_grounding(
        "Students should contact the instructor in writing before the deadline [handbook_chunk_1].",
        evidence,
    )
    assert result.status == GroundingStatus.GROUNDED
    assert result.score == 1.0


def test_without_evidence_is_not_applicable():
    result = check_grounding("A generic response.", [])
    assert result.status == GroundingStatus.NOT_APPLICABLE


def test_native_tool_outputs_are_grounding_evidence():
    evidence = [
        {
            "tool_name": "calendar_search",
            "output": {
                "events": [
                    {
                        "title": "DAA Assignment 2",
                        "date": "2026-06-14",
                        "type": "deadline",
                        "course": "CSN-252",
                    }
                ]
            },
        },
        {
            "tool_name": "email_send_mock",
            "output": {
                "receipt_id": "mock_123",
                "message": "The approved action was simulated; no real email was sent.",
            },
        },
    ]
    result = check_grounding(
        "DAA Assignment 2 is on 2026-06-14. "
        "The approved action was simulated; no real email was sent.",
        evidence,
    )
    assert result.status == GroundingStatus.GROUNDED
