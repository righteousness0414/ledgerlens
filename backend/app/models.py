from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    storage_path: Mapped[str] = mapped_column(String(1024))
    # uploaded | processing | extracted | reviewed | approved | failed
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    extractions: Mapped[List["Extraction"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Extraction.id",
    )
    audit_entries: Mapped[List["AuditLog"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="AuditLog.id",
    )

    @property
    def latest_extraction(self) -> Optional["Extraction"]:
        return self.extractions[-1] if self.extractions else None


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="extractions")
    fields: Mapped[List["Field"]] = relationship(
        back_populates="extraction",
        cascade="all, delete-orphan",
        order_by="Field.id",
    )
    line_items: Mapped[List["LineItem"]] = relationship(
        back_populates="extraction",
        cascade="all, delete-orphan",
        order_by="LineItem.id",
    )


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey("extractions.id"))
    # supplier | invoice_number | date | vat | total | currency | subtotal
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    model_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[str] = mapped_column(String(8), default="n/a")  # pass|fail|n/a
    validation_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    final_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    corrected_value: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    corrected_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    corrected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    extraction: Mapped["Extraction"] = relationship(back_populates="fields")

    @property
    def effective_value(self) -> Optional[str]:
        return self.corrected_value if self.corrected_value is not None else self.value


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey("extractions.id"))
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    extraction: Mapped["Extraction"] = relationship(back_populates="line_items")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    action: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(128), default="reviewer")
    before_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="audit_entries")
