from typing import Any

from pydantic import BaseModel, Field


class DocumentSearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    corpus: str = Field(default="all", pattern="^(all|handbook|internship|course|club)$")
    top_k: int = Field(default=3, ge=1, le=5)
    include_snippets: bool = True


class DocumentResult(BaseModel):
    document_id: str
    source_id: str
    title: str
    snippet: str
    citation: str
    score: float
    metadata: dict[str, Any]


class DocumentSearchOutput(BaseModel):
    results: list[DocumentResult]
    untrusted_content: bool = True
