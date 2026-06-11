from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field


class CalendarSearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    days: int = Field(default=14, ge=1, le=90)


class CalendarEvent(BaseModel):
    title: str
    date: str
    type: Literal["deadline", "class", "meeting"]
    course: str


class CalendarSearchOutput(BaseModel):
    events: list[CalendarEvent]


def calendar_search(input_data: CalendarSearchInput) -> CalendarSearchOutput:
    today = date.today()
    events = [
        CalendarEvent(
            title="DAA Assignment 2",
            date=str(today + timedelta(days=3)),
            type="deadline",
            course="CSN-252",
        ),
        CalendarEvent(
            title="MAC Problem Set 4",
            date=str(today + timedelta(days=6)),
            type="deadline",
            course="MAC-301",
        ),
        CalendarEvent(
            title="Algorithms office hours",
            date=str(today + timedelta(days=2)),
            type="meeting",
            course="CSN-252",
        ),
    ]
    query_words = {word.lower() for word in input_data.query.split()}
    filtered = [
        event
        for event in events
        if not query_words
        or any(word in f"{event.title} {event.course} {event.type}".lower() for word in query_words)
    ]
    return CalendarSearchOutput(events=filtered or events[:2])


class EmailDraftInput(BaseModel):
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=2, max_length=5_000)


class EmailDraftOutput(BaseModel):
    draft_id: str
    to: str
    subject: str
    body: str
    sendable: bool = False


def email_draft(input_data: EmailDraftInput) -> EmailDraftOutput:
    import hashlib

    digest = hashlib.sha256(
        f"{input_data.to}:{input_data.subject}:{input_data.body}".encode()
    ).hexdigest()[:10]
    return EmailDraftOutput(draft_id=f"draft_{digest}", **input_data.model_dump())


class EmailSendMockInput(BaseModel):
    draft_id: str = Field(min_length=3, max_length=120)
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=2, max_length=200)
    body_preview: str = Field(min_length=2, max_length=1_000)
    send_mode: Literal["simulation"] = "simulation"
    attachments: list[str] = Field(default_factory=list, max_length=0)


class EmailSendMockOutput(BaseModel):
    receipt_id: str
    delivered: bool = False
    message: str


def email_send_mock(input_data: EmailSendMockInput) -> EmailSendMockOutput:
    import hashlib

    digest = hashlib.sha256(input_data.model_dump_json().encode()).hexdigest()[:12]
    return EmailSendMockOutput(
        receipt_id=f"mock_{digest}",
        message=f"Simulated delivery to {input_data.to}; no external email was sent.",
    )
