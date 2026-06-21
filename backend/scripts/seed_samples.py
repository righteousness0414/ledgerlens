#!/usr/bin/env python3
"""Generate synthetic invoice samples into ../samples (PDF + PNG).

Each sample is paired with a ``<name>.json`` ground-truth sidecar so the `mock`
extractor returns data that matches the rendered document — the demo loop stays
coherent with zero API keys. All data is fabricated; no real records are used.

Usage:  python scripts/seed_samples.py
Requires reportlab (see requirements.txt, optional block).
"""
from __future__ import annotations

import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# Synthetic invoices. One has a deliberate VAT mismatch + a low-confidence field
# so the confidence/validation loop visibly flags something to review.
SAMPLES = [
    {
        "name": "invoice_northwind_2025-0042",
        "supplier": "Northwind Office Supplies Ltd",
        "invoice_number": "INV-2025-0042",
        "date": "2025-03-14",
        "currency": "GBP",
        "subtotal": 1240.00,
        "vat": 248.00,
        "total": 1488.00,
        "vat_rate": 0.20,
        "line_items": [
            {"description": "Ergonomic chairs", "qty": 4, "unit_price": 180.00, "amount": 720.00, "confidence": 0.96},
            {"description": "Standing desks", "qty": 2, "unit_price": 260.00, "amount": 520.00, "confidence": 0.95},
        ],
        "_confidence": {"supplier": 0.98, "invoice_number": 0.72, "date": 0.95,
                        "currency": 0.99, "subtotal": 0.94, "vat": 0.93, "total": 0.95},
    },
    {
        "name": "invoice_acme_2025-1187",
        "supplier": "Acme Industrial GmbH",
        "invoice_number": "INV-2025-1187",
        "date": "2025-05-02",
        "currency": "EUR",
        "subtotal": 3200.00,
        "vat": 615.00,        # deliberately wrong (should be 608.00 @ 19%)
        "total": 3808.00,
        "vat_rate": 0.19,
        "line_items": [
            {"description": "Steel brackets (box)", "qty": 10, "unit_price": 140.00, "amount": 1400.00, "confidence": 0.93},
            {"description": "Industrial fasteners", "qty": 1, "unit_price": 1800.00, "amount": 1800.00, "confidence": 0.9},
        ],
        "_confidence": {"supplier": 0.97, "invoice_number": 0.9, "date": 0.94,
                        "currency": 0.98, "subtotal": 0.92, "vat": 0.88, "total": 0.91},
    },
]


def _write_sidecar(sample: dict) -> None:
    (SAMPLES_DIR / f"{sample['name']}.json").write_text(json.dumps(sample, indent=2))


def _render_pdf(sample: dict) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    path = SAMPLES_DIR / f"{sample['name']}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 30 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, sample["supplier"])
    c.setFont("Helvetica", 10)
    y -= 12 * mm
    c.drawString(20 * mm, y, f"Invoice: {sample['invoice_number']}")
    c.drawString(120 * mm, y, f"Date: {sample['date']}")
    y -= 14 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Description")
    c.drawString(110 * mm, y, "Qty")
    c.drawString(130 * mm, y, "Unit")
    c.drawString(160 * mm, y, "Amount")
    c.setFont("Helvetica", 10)
    for li in sample["line_items"]:
        y -= 8 * mm
        c.drawString(20 * mm, y, str(li["description"]))
        c.drawString(110 * mm, y, str(li["qty"]))
        c.drawString(130 * mm, y, f"{li['unit_price']:.2f}")
        c.drawString(160 * mm, y, f"{li['amount']:.2f}")

    cur = sample["currency"]
    y -= 16 * mm
    for label, key in (("Subtotal", "subtotal"), ("VAT", "vat"), ("Total", "total")):
        c.drawString(130 * mm, y, label)
        c.drawString(160 * mm, y, f"{cur} {sample[key]:.2f}")
        y -= 8 * mm
    c.showPage()
    c.save()


def _render_png(sample: dict) -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return  # PNG is optional; PDF is enough for the demo.
    img = Image.new("RGB", (800, 600), "white")
    d = ImageDraw.Draw(img)
    lines = [
        sample["supplier"],
        f"Invoice: {sample['invoice_number']}   Date: {sample['date']}",
        "",
        *[f"{li['description']}  x{li['qty']}  {li['amount']:.2f}" for li in sample["line_items"]],
        "",
        f"Subtotal: {sample['currency']} {sample['subtotal']:.2f}",
        f"VAT: {sample['currency']} {sample['vat']:.2f}",
        f"Total: {sample['currency']} {sample['total']:.2f}",
    ]
    y = 30
    for ln in lines:
        d.text((30, y), ln, fill="black")
        y += 28
    img.save(SAMPLES_DIR / f"{sample['name']}.png")


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for sample in SAMPLES:
        _write_sidecar(sample)
        try:
            _render_pdf(sample)
        except ImportError:
            print("reportlab not installed — skipping PDF (install it to render samples).")
        _render_png(sample)
        print(f"seeded {sample['name']}")
    print(f"\nSamples written to {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
