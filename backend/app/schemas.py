from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str | None
    qty: float | None
    unit_price: float | None
    amount: float | None
    confidence: float


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str | None
    model_confidence: float
    validation_status: str
    validation_message: str | None
    final_confidence: float
    flagged: bool
    corrected_value: str | None
    corrected_by: str | None
    corrected_at: datetime | None
    effective_value: str | None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    mime_type: str
    status: str
    created_at: datetime


class DocumentDetail(DocumentSummary):
    provider: str | None = None
    model: str | None = None
    fields: list[FieldOut] = []
    line_items: list[LineItemOut] = []
    flagged_count: int = 0


class FieldUpdate(BaseModel):
    value: str
    actor: str = "reviewer"


class ApproveRequest(BaseModel):
    actor: str = "reviewer"


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    actor: str
    before_json: str | None
    after_json: str | None
    created_at: datetime
