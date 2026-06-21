from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, stubs
from app.config import get_settings
from app.db import init_db

settings = get_settings()

app = FastAPI(
    title="LedgerLens API",
    description="Reviewer-in-the-loop accounting document processing: "
    "extract → confidence → human review → export.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "provider": settings.extraction_provider}


app.include_router(documents.router)
app.include_router(stubs.router)
