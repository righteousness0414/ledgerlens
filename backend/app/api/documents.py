from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.schemas import (
    ApproveRequest,
    DocumentDetail,
    DocumentSummary,
    FieldOut,
    FieldUpdate,
    LineItemOut,
)
from app.services import export
from app.services.confidence import score
from app.services.extraction import get_extractor
from app.services.storage import storage

router = APIRouter(prefix="/documents", tags=["documents"])


def _run_extraction(db: Session, document: models.Document) -> None:
    """Extract → score → persist. Sets status to extracted (or failed)."""
    document.status = "processing"
    db.commit()
    try:
        content = storage.read(document.storage_path)
        extractor = get_extractor()
        result = extractor.extract(content, document.mime_type, document.filename)
        scored = score(result)

        extraction = models.Extraction(
            document_id=document.id,
            provider=result.provider,
            model=result.model,
            raw_json=json.dumps(result.raw, default=str)[:1_000_000],
        )
        for sf in scored:
            extraction.fields.append(
                models.Field(
                    key=sf.key,
                    value=sf.value,
                    model_confidence=sf.model_confidence,
                    validation_status=sf.validation_status,
                    validation_message=sf.validation_message,
                    final_confidence=sf.final_confidence,
                    flagged=sf.flagged,
                )
            )
        for li in result.line_items:
            extraction.line_items.append(
                models.LineItem(
                    description=li.description,
                    qty=li.qty,
                    unit_price=li.unit_price,
                    amount=li.amount,
                    confidence=li.confidence,
                )
            )
        document.extractions.append(extraction)
        document.status = "extracted"
        db.commit()
    except Exception as exc:  # noqa: BLE001 — surface failure as status, don't 500 the upload
        document.status = "failed"
        db.add(
            models.AuditLog(
                document_id=document.id,
                action="extraction_failed",
                actor="system",
                after_json=json.dumps({"error": str(exc)}),
            )
        )
        db.commit()


def _detail(document: models.Document) -> DocumentDetail:
    extraction = document.latest_extraction
    fields = [FieldOut.model_validate(f) for f in extraction.fields] if extraction else []
    items = [LineItemOut.model_validate(li) for li in extraction.line_items] if extraction else []
    return DocumentDetail(
        id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        status=document.status,
        created_at=document.created_at,
        provider=extraction.provider if extraction else None,
        model=extraction.model if extraction else None,
        fields=fields,
        line_items=items,
        flagged_count=sum(1 for f in fields if f.flagged),
    )


@router.post("", response_model=DocumentDetail)
def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> DocumentDetail:
    content = file.file.read()
    if not content:
        raise HTTPException(400, "empty file")
    path = storage.save(content, file.filename or "upload")
    document = models.Document(
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        storage_path=path,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    _run_extraction(db, document)
    db.refresh(document)
    return _detail(document)


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentSummary]:
    docs = db.scalars(select(models.Document).order_by(models.Document.id.desc())).all()
    return [DocumentSummary.model_validate(d) for d in docs]


def _get(db: Session, document_id: int) -> models.Document:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    return doc


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentDetail:
    return _detail(_get(db, document_id))


@router.get("/{document_id}/file")
def get_document_file(document_id: int, db: Session = Depends(get_db)) -> Response:
    """Serve the original uploaded file (for the side-by-side review pane)."""
    document = _get(db, document_id)
    content = storage.read(document.storage_path)
    # Inline so PDFs render in an <iframe> and images in an <img>.
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'inline; filename="{document.filename}"'},
    )


@router.patch("/{document_id}/fields/{field_id}", response_model=FieldOut)
def correct_field(
    document_id: int,
    field_id: int,
    update: FieldUpdate,
    db: Session = Depends(get_db),
) -> FieldOut:
    document = _get(db, document_id)
    field = db.get(models.Field, field_id)
    extraction = document.latest_extraction
    if field is None or extraction is None or field.extraction_id != extraction.id:
        raise HTTPException(404, "field not found on this document")

    before = {"value": field.value, "corrected_value": field.corrected_value}
    field.corrected_value = update.value
    field.corrected_by = update.actor
    field.corrected_at = datetime.now(timezone.utc)
    # A human correction is ground truth — clear the flag and max the confidence.
    field.flagged = False
    field.final_confidence = 1.0

    db.add(
        models.AuditLog(
            document_id=document.id,
            action="field_corrected",
            actor=update.actor,
            before_json=json.dumps(before),
            after_json=json.dumps({"corrected_value": update.value, "key": field.key}),
        )
    )
    if document.status == "extracted":
        document.status = "reviewed"
    db.commit()
    db.refresh(field)
    return FieldOut.model_validate(field)


@router.post("/{document_id}/approve", response_model=DocumentDetail)
def approve_document(
    document_id: int,
    body: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document = _get(db, document_id)
    if document.latest_extraction is None:
        raise HTTPException(400, "nothing to approve — document not extracted")
    actor = body.actor if body else "reviewer"
    document.status = "approved"
    db.add(models.AuditLog(document_id=document.id, action="approved", actor=actor))
    db.commit()
    db.refresh(document)
    return _detail(document)


@router.get("/{document_id}/export")
def export_document(
    document_id: int,
    format: str = "csv",
    db: Session = Depends(get_db),
) -> Response:
    document = _get(db, document_id)
    fmt = format.lower()
    if fmt == "csv":
        data = export.to_csv([document])
        media, ext = "text/csv", "csv"
    elif fmt in ("xlsx", "excel"):
        data = export.to_xlsx([document])
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        raise HTTPException(400, "format must be csv or xlsx")
    filename = f"ledgerlens_doc_{document_id}.{ext}"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
