from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

# Canonical field keys LedgerLens extracts and scores.
FIELD_KEYS = ["supplier", "invoice_number", "date", "currency", "subtotal", "vat", "total"]


@dataclass
class ExtractedField:
    key: str
    value: str | None
    confidence: float


@dataclass
class ExtractedLineItem:
    description: str | None = None
    qty: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    provider: str
    model: str
    fields: list[ExtractedField] = field(default_factory=list)
    line_items: list[ExtractedLineItem] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


class Extractor(Protocol):
    """Provider-swappable extraction interface.

    Every provider (mock / claude / openai / google_vision) returns the
    same normalized ``ExtractionResult`` so the rest of the pipeline —
    validation, confidence, review, export — is provider-agnostic.
    """

    name: str

    def extract(self, content: bytes, mime_type: str, filename: str) -> ExtractionResult: ...
