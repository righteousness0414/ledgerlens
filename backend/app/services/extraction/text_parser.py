from __future__ import annotations

import re

from app.services.extraction.base import (
    ExtractedField,
    ExtractedLineItem,
    ExtractionResult,
)

# Deterministic OCR-text → field extraction. This mirrors the family-business
# Cloud Vision pipeline: Vision returns raw text, and regex/heuristics turn it
# into structured fields. No model judgement, so confidence is rule-based.

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"}

_DATE_PATTERNS = [
    r"\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\b",
    r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})\b",
]
_INVOICE_PATTERNS = [
    r"invoice\s*(?:no\.?|number|#)?\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-/]{2,})",
    r"\bINV[-/]?[A-Za-z0-9\-/]{2,}\b",
]
_MONEY = r"([0-9][0-9,]*\.?\d{0,2})"


def _amount(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _search(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    return None


def _labeled_amount(label: str, text: str) -> str | None:
    m = re.search(rf"{label}\s*[:]?\s*[^\d\-]*{_MONEY}", text, re.IGNORECASE)
    return m.group(1) if m else None


def parse_text(text: str, provider: str, model: str) -> ExtractionResult:
    fields: list[ExtractedField] = []

    # Supplier: first non-empty line is a decent heuristic for receipts/invoices.
    supplier = next((ln.strip() for ln in text.splitlines() if ln.strip()), None)
    fields.append(ExtractedField("supplier", supplier, 0.8 if supplier else 0.0))

    invoice = _search(_INVOICE_PATTERNS, text)
    fields.append(ExtractedField("invoice_number", invoice, 0.85 if invoice else 0.3))

    date = _search(_DATE_PATTERNS, text)
    fields.append(ExtractedField("date", date, 0.85 if date else 0.3))

    currency = None
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            currency = code
            break
    if currency is None:
        for code in _CURRENCY_CODES:
            if re.search(rf"\b{code}\b", text):
                currency = code
                break
    fields.append(ExtractedField("currency", currency, 0.9 if currency else 0.4))

    subtotal = _labeled_amount("sub[\\- ]?total", text)
    vat = _labeled_amount("(?:vat|tax|gst)", text)
    total = _labeled_amount("(?:grand[\\- ]?total|total|amount due|balance due)", text)

    fields.append(ExtractedField("subtotal", subtotal, 0.85 if subtotal else 0.4))
    fields.append(ExtractedField("vat", vat, 0.8 if vat else 0.4))
    fields.append(ExtractedField("total", total, 0.88 if total else 0.4))

    # Line items: lines that end in a money amount.
    items: list[ExtractedLineItem] = []
    for ln in text.splitlines():
        m = re.search(rf"^(.*?)\s+{_MONEY}\s*$", ln.strip())
        if m and m.group(1) and not re.search(r"total|vat|tax|subtotal", m.group(1), re.I):
            items.append(
                ExtractedLineItem(
                    description=m.group(1).strip(),
                    amount=_amount(m.group(2)),
                    confidence=0.7,
                )
            )

    return ExtractionResult(
        provider=provider,
        model=model,
        fields=fields,
        line_items=items[:20],
        raw={"ocr_text": text[:5000]},
    )
