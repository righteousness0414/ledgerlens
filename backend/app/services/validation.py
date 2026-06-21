from __future__ import annotations

import re
from dataclasses import dataclass

from dateutil import parser as date_parser

from app.config import get_settings
from app.services.extraction.base import ExtractedLineItem

settings = get_settings()

# ISO 4217 — the common subset is enough for the PoC; extend per client.
_ISO_4217 = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "HKD",
    "SGD", "SEK", "NOK", "DKK", "INR", "BRL", "ZAR", "MXN", "KRW", "PLN",
}

# pass | fail | n/a
PASS, FAIL, NA = "pass", "fail", "n/a"


@dataclass
class FieldCheck:
    status: str
    message: str | None = None


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def check_date(value: str | None) -> FieldCheck:
    if not value:
        return FieldCheck(NA, "no date extracted")
    try:
        date_parser.parse(value)
        return FieldCheck(PASS)
    except (ValueError, OverflowError):
        return FieldCheck(FAIL, f"'{value}' is not a valid date")


def check_currency(value: str | None) -> FieldCheck:
    if not value:
        return FieldCheck(NA, "no currency extracted")
    return (
        FieldCheck(PASS)
        if value.upper() in _ISO_4217
        else FieldCheck(FAIL, f"'{value}' is not a valid ISO 4217 code")
    )


def check_invoice_number(value: str | None) -> FieldCheck:
    if not value:
        return FieldCheck(NA, "no invoice number extracted")
    pattern = settings.invoice_number_regex
    return (
        FieldCheck(PASS)
        if re.match(pattern, value)
        else FieldCheck(FAIL, f"'{value}' does not match expected pattern")
    )


def check_totals(subtotal: str | None, vat: str | None, total: str | None) -> FieldCheck:
    """vat/total consistency: subtotal + vat ≈ total (1 cent tolerance)."""
    s, v, t = _to_float(subtotal), _to_float(vat), _to_float(total)
    if t is None or (s is None and v is None):
        return FieldCheck(NA, "insufficient amounts to verify")
    expected = (s or 0.0) + (v or 0.0)
    if abs(expected - t) <= 0.01:
        return FieldCheck(PASS)
    return FieldCheck(FAIL, f"subtotal+vat ({expected:.2f}) ≠ total ({t:.2f})")


def check_line_items(items: list[ExtractedLineItem], subtotal: str | None) -> FieldCheck:
    if not items:
        return FieldCheck(NA, "no line items")
    s = _to_float(subtotal)
    line_sum = sum(li.amount for li in items if li.amount is not None)
    if s is None:
        return FieldCheck(NA, "no subtotal to compare")
    # 1% tolerance for rounding in line-level amounts.
    if abs(line_sum - s) <= max(0.01, abs(s) * 0.01):
        return FieldCheck(PASS)
    return FieldCheck(FAIL, f"line items sum ({line_sum:.2f}) ≠ subtotal ({s:.2f})")


def validate(values: dict[str, str | None], items: list[ExtractedLineItem]) -> dict[str, FieldCheck]:
    """Run every deterministic check and return per-field results.

    Keys map to ``fields.key``; ``total`` carries the totals-consistency check,
    ``subtotal`` carries the line-item check, so each is surfaced on its field.
    """
    return {
        "date": check_date(values.get("date")),
        "currency": check_currency(values.get("currency")),
        "invoice_number": check_invoice_number(values.get("invoice_number")),
        "total": check_totals(values.get("subtotal"), values.get("vat"), values.get("total")),
        "vat": check_totals(values.get("subtotal"), values.get("vat"), values.get("total")),
        "subtotal": check_line_items(items, values.get("subtotal")),
    }
