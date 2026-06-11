import re
from dataclasses import dataclass
from typing import Any

from .domain import GroundingStatus

WORD_RE = re.compile(r"[a-zA-Z0-9_-]+")


def words(text: str) -> set[str]:
    return {
        word.lower()
        for word in WORD_RE.findall(text)
        if len(word) > 3 and word.lower() not in {"that", "this", "with", "from", "have", "your"}
    }


@dataclass(frozen=True)
class GroundingResult:
    status: GroundingStatus
    score: float | None
    details: dict[str, Any]


def check_grounding(final_answer: str, evidence: list[dict[str, Any]]) -> GroundingResult:
    normalized_answer = final_answer.lower()
    if (
        "could not find supporting tool evidence" in normalized_answer
        or "not asserting an answer" in normalized_answer
    ):
        return GroundingResult(
            GroundingStatus.NOT_APPLICABLE,
            None,
            {"supporting_sources": [], "claims": [], "unsupported_claims": []},
        )

    snippets: list[dict[str, Any]] = []
    for item in evidence:
        tool_name = item.get("tool_name")
        output = item.get("output", {})
        if tool_name == "document_search":
            snippets.extend(result for result in output.get("results", []) if result.get("snippet"))
        elif tool_name == "calendar_search":
            for event in output.get("events", []):
                snippets.append(
                    {
                        "source_id": f"calendar_{event['course']}_{event['date']}",
                        "title": "Academic Calendar",
                        "snippet": (
                            f"{event['title']} on {event['date']} for {event['course']} "
                            f"is a {event['type']}."
                        ),
                        "kind": "calendar",
                    }
                )
        elif tool_name == "email_draft":
            snippets.append(
                {
                    "source_id": output.get("draft_id", "tool_email_draft"),
                    "title": "Local Draft Artifact",
                    "snippet": (
                        f"Created a local draft email to {output.get('to', '')} "
                        f"with subject {output.get('subject', '')}."
                    ),
                    "kind": "tool_output",
                }
            )
        elif tool_name == "email_send_mock":
            snippets.append(
                {
                    "source_id": output.get("receipt_id", "tool_email_send_mock"),
                    "title": "Mock Send Receipt",
                    "snippet": output.get("message", "The external action was simulated."),
                    "kind": "tool_output",
                }
            )
    if not snippets:
        return GroundingResult(
            GroundingStatus.NOT_APPLICABLE,
            None,
            {"supporting_sources": [], "claims": [], "unsupported_claims": []},
        )

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", final_answer)
        if sentence.strip()
    ]
    claims: list[dict[str, Any]] = []
    supported = 0
    for sentence in sentences:
        sentence_words = words(sentence)
        best_score = 0.0
        best_source: str | None = None
        cited_sources = re.findall(r"\[([a-zA-Z0-9_-]+)\]", sentence)
        for snippet in snippets:
            overlap = len(sentence_words & words(snippet["snippet"]))
            score = overlap / max(len(sentence_words), 1)
            if cited_sources and snippet["source_id"] in cited_sources:
                score += 0.35
            if score > best_score:
                best_score = score
                best_source = snippet["source_id"]
        is_supported = best_score >= 0.25
        supported += int(is_supported)
        claims.append(
            {
                "claim": sentence,
                "supported": is_supported,
                "score": round(min(best_score, 1.0), 3),
                "source_id": best_source,
            }
        )

    ratio = supported / max(len(claims), 1)
    if ratio >= 0.8:
        status = GroundingStatus.GROUNDED
    elif ratio >= 0.4:
        status = GroundingStatus.PARTIALLY_GROUNDED
    else:
        status = GroundingStatus.UNSUPPORTED
    return GroundingResult(
        status,
        round(ratio, 3),
        {
            "supporting_sources": sorted(
                {
                    claim["source_id"]
                    for claim in claims
                    if claim["supported"] and claim["source_id"]
                }
            ),
            "evidence_sources": [
                {
                    "source_id": snippet["source_id"],
                    "title": snippet.get("title", "Tool Evidence"),
                    "snippet": snippet["snippet"],
                    "kind": snippet.get("kind", "document"),
                }
                for snippet in snippets
            ],
            "claims": claims,
            "unsupported_claims": [claim["claim"] for claim in claims if not claim["supported"]],
        },
    )
