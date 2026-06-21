from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services.extraction.base import (
    ExtractedField,
    ExtractedLineItem,
    ExtractionResult,
)

# A small deterministic catalogue so demos are stable and offline.
_SUPPLIERS = [
    ("Northwind Office Supplies Ltd", "GBP", 0.20),
    ("Acme Industrial GmbH", "EUR", 0.19),
    ("Pacific Components Inc", "USD", 0.0),
    ("Sakura Trading K.K.", "JPY", 0.10),
]


def _pick(seed: str, options: list) -> object:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


class MockExtractor:
    """Deterministic, offline, key-free extractor.

    If a ground-truth sidecar ``<sample>.json`` sits next to the uploaded
    file (written by ``scripts/seed_samples.py``), it is used so the rendered
    document and the extracted fields stay consistent. Otherwise a stable
    synthetic invoice is derived from the filename hash.

    The result is intentionally *imperfect*: one field carries low model
    confidence and the VAT is slightly off, so the confidence + validation
    loop has something to flag — that's the whole point of the demo.
    """

    name = "mock"
    model = "mock-deterministic-v1"

    def extract(self, content: bytes, mime_type: str, filename: str) -> ExtractionResult:
        sidecar = self._load_sidecar(filename)
        if sidecar is not None:
            return self._from_sidecar(sidecar)
        return self._synthetic(filename)

    def _load_sidecar(self, filename: str) -> dict | None:
        # filename here is the original name; samples live in ./samples.
        for base in (Path("samples"), Path(".")):
            candidate = base / (Path(filename).stem + ".json")
            if candidate.exists():
                try:
                    return json.loads(candidate.read_text())
                except (OSError, json.JSONDecodeError):
                    return None
        return None

    def _from_sidecar(self, data: dict) -> ExtractionResult:
        conf = data.get("_confidence", {})
        fields = [
            ExtractedField(key=k, value=_str(data.get(k)), confidence=float(conf.get(k, 0.97)))
            for k in ("supplier", "invoice_number", "date", "currency", "subtotal", "vat", "total")
        ]
        items = [
            ExtractedLineItem(
                description=li.get("description"),
                qty=li.get("qty"),
                unit_price=li.get("unit_price"),
                amount=li.get("amount"),
                confidence=float(li.get("confidence", 0.95)),
            )
            for li in data.get("line_items", [])
        ]
        return ExtractionResult(
            provider=self.name, model=self.model, fields=fields, line_items=items, raw=data
        )

    def _synthetic(self, filename: str) -> ExtractionResult:
        supplier, currency, vat_rate = _pick(filename, _SUPPLIERS)
        h = int(hashlib.sha256(filename.encode()).hexdigest(), 16)
        invoice_no = f"INV-{2024}-{h % 9000 + 1000}"
        day = h % 27 + 1
        date = f"2025-{(h % 12) + 1:02d}-{day:02d}"

        subtotal = round(120 + (h % 880) + (h % 100) / 100, 2)
        vat = round(subtotal * vat_rate, 2)
        # Inject a small VAT error so deterministic validation flags it.
        vat_reported = round(vat + 0.07, 2)
        total = round(subtotal + vat, 2)

        items = [
            ExtractedLineItem("Consulting services", 1, subtotal * 0.6, round(subtotal * 0.6, 2), 0.96),
            ExtractedLineItem("Materials", 2, subtotal * 0.2, round(subtotal * 0.4, 2), 0.9),
        ]

        fields = [
            ExtractedField("supplier", supplier, 0.97),
            # Low model confidence → flagged even though it passes validation.
            ExtractedField("invoice_number", invoice_no, 0.71),
            ExtractedField("date", date, 0.95),
            ExtractedField("currency", currency, 0.99),
            ExtractedField("subtotal", f"{subtotal:.2f}", 0.93),
            ExtractedField("vat", f"{vat_reported:.2f}", 0.9),
            ExtractedField("total", f"{total:.2f}", 0.94),
        ]
        raw = {"_note": "synthetic mock extraction", "vat_rate": vat_rate}
        return ExtractionResult(
            provider=self.name, model=self.model, fields=fields, line_items=items, raw=raw
        )


def _str(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)
