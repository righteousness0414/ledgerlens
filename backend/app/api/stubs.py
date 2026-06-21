from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

# Auth/RBAC and accounting-system sync are intentionally out of scope for the
# PoC. These mock adapters return realistic shapes so the
# end-to-end flow and the future integration surface are both visible.

router = APIRouter(tags=["stubs"])


class LoginRequest(BaseModel):
    email: str
    password: str = ""


class LoginResponse(BaseModel):
    token: str
    user: dict
    note: str


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    return LoginResponse(
        token="mock-jwt-token",
        user={"email": body.email, "role": "reviewer"},
        note="Mock auth — replace with real RBAC for production (see Roadmap).",
    )


class QuickBooksSyncResponse(BaseModel):
    synced: bool
    quickbooks_txn_id: str
    document_id: int
    note: str


@router.post("/documents/{document_id}/sync/quickbooks", response_model=QuickBooksSyncResponse)
def sync_quickbooks(document_id: int, db: Session = Depends(get_db)) -> QuickBooksSyncResponse:
    document = db.get(models.Document, document_id)
    if document is None:
        raise HTTPException(404, "document not found")
    if document.status != "approved":
        raise HTTPException(400, "approve the document before syncing")
    db.add(
        models.AuditLog(
            document_id=document.id, action="quickbooks_sync", actor="system"
        )
    )
    db.commit()
    return QuickBooksSyncResponse(
        synced=True,
        quickbooks_txn_id=f"QBO-MOCK-{document_id:06d}",
        document_id=document_id,
        note="Mock QuickBooks Online adapter — maps approved data to a QBO bill.",
    )
