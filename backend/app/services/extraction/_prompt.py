from __future__ import annotations

# Shared extraction contract used by the vision-LLM providers (Claude / OpenAI).
# Each field is returned as {value, confidence} so the model self-assesses, which
# is one of the two signals the confidence engine combines (the other is
# deterministic validation; see services/confidence.py).

FIELD_KEYS = ["supplier", "invoice_number", "date", "currency", "subtotal", "vat", "total"]

SYSTEM_PROMPT = (
    "You are an accounting-document extraction engine. Extract structured fields "
    "from invoices, receipts, and supplier bills. Return ONLY data that is present "
    "in the document. For every field, return a value (string, or null if absent) "
    "and a confidence in [0,1] reflecting how certain you are of that exact value. "
    "Dates must be ISO 8601 (YYYY-MM-DD). Currency must be an ISO 4217 code "
    "(USD, EUR, GBP, JPY, ...). Amounts must be plain decimal strings with no "
    "currency symbol or thousands separators."
)

USER_PROMPT = (
    "Extract the accounting fields and line items from this document. "
    "Fields: supplier, invoice_number, date, currency, subtotal, vat, total."
)

# JSON Schema for structured output. A field object is {value, confidence}.
_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": ["value", "confidence"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        **{k: _FIELD_SCHEMA for k in FIELD_KEYS},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": ["string", "null"]},
                    "qty": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "amount": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                },
                "required": ["description", "qty", "unit_price", "amount", "confidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": [*FIELD_KEYS, "line_items"],
    "additionalProperties": False,
}


def parse_payload(data: dict, provider: str, model: str):
    """Turn a schema-conformant dict into an ExtractionResult."""
    from app.services.extraction.base import (
        ExtractedField,
        ExtractedLineItem,
        ExtractionResult,
    )

    fields = []
    for k in FIELD_KEYS:
        obj = data.get(k) or {}
        val = obj.get("value")
        fields.append(
            ExtractedField(
                key=k,
                value=None if val is None else str(val),
                confidence=float(obj.get("confidence", 0.0)),
            )
        )
    items = [
        ExtractedLineItem(
            description=li.get("description"),
            qty=li.get("qty"),
            unit_price=li.get("unit_price"),
            amount=li.get("amount"),
            confidence=float(li.get("confidence", 0.0)),
        )
        for li in data.get("line_items", [])
    ]
    return ExtractionResult(
        provider=provider, model=model, fields=fields, line_items=items, raw=data
    )
