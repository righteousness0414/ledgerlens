from __future__ import annotations

import csv
import io

from openpyxl import Workbook

from app.models import Document

# Column order for exported transactions.
_COLUMNS = ["supplier", "invoice_number", "date", "currency", "subtotal", "vat", "total"]


def _row(document: Document) -> dict[str, str]:
    extraction = document.latest_extraction
    values = {c: "" for c in _COLUMNS}
    values["document_id"] = str(document.id)
    values["filename"] = document.filename
    values["status"] = document.status
    if extraction:
        for field in extraction.fields:
            if field.key in values:
                values[field.key] = field.effective_value or ""
    return values


_HEADER = ["document_id", "filename", "status", *_COLUMNS]


def to_csv(documents: list[Document]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_HEADER)
    writer.writeheader()
    for doc in documents:
        writer.writerow(_row(doc))
    return buf.getvalue().encode("utf-8")


def to_xlsx(documents: list[Document]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    ws.append(_HEADER)
    for doc in documents:
        row = _row(doc)
        ws.append([row.get(col, "") for col in _HEADER])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
