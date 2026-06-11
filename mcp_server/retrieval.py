import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

DOCUMENT_DIR = Path(__file__).resolve().parent / "documents"
TOKEN_RE = re.compile(r"[a-zA-Z0-9_-]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2]


def load_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for path in sorted(DOCUMENT_DIR.glob("*.txt")):
        title, *paragraphs = path.read_text(encoding="utf-8").split("\n\n")
        corpus = path.stem.split("_")[0]
        for index, paragraph in enumerate(paragraphs, start=1):
            normalized = " ".join(paragraph.split())
            if not normalized:
                continue
            chunks.append(
                {
                    "document_id": path.stem,
                    "source_id": f"{path.stem}_chunk_{index}",
                    "title": title,
                    "snippet": normalized,
                    "citation": f"{path.stem}:{index}",
                    "metadata": {
                        "corpus": corpus,
                        "page": index,
                        "filename": path.name,
                    },
                }
            )
    return chunks


def search_documents(
    query: str, corpus: str = "all", top_k: int = 3
) -> list[dict[str, Any]]:
    chunks = [
        chunk
        for chunk in load_chunks()
        if corpus == "all" or chunk["metadata"]["corpus"] == corpus
    ]
    query_tokens = tokenize(query)
    document_frequency = Counter()
    for chunk in chunks:
        document_frequency.update(set(tokenize(chunk["snippet"])))

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        counts = Counter(tokenize(chunk["snippet"]))
        score = 0.0
        for token in query_tokens:
            if counts[token]:
                inverse_frequency = (
                    math.log((len(chunks) + 1) / (document_frequency[token] + 1)) + 1
                )
                score += counts[token] * inverse_frequency
        if score > 0:
            result = dict(chunk)
            result["score"] = round(score, 4)
            scored.append((score, result))

    scored.sort(key=lambda item: (-item[0], item[1]["source_id"]))
    return [result for _, result in scored[:top_k]]
