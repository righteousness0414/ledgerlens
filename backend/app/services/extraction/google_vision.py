from __future__ import annotations

from app.services.extraction.base import ExtractionResult
from app.services.extraction.text_parser import parse_text


class GoogleVisionExtractor:
    """Google Cloud Vision OCR → deterministic field parsing.

    This reproduces the production family-business approach: Cloud Vision does
    DOCUMENT_TEXT_DETECTION, then deterministic rules (``text_parser``) turn the
    raw OCR text into structured fields. No LLM is involved — it satisfies the
    "works on Cloud Vision" requirement and is fully auditable.

    Auth uses GOOGLE_APPLICATION_CREDENTIALS (a service-account JSON path).
    """

    name = "google_vision"
    model = "cloud-vision-document-text-detection"

    def extract(self, content: bytes, mime_type: str, filename: str) -> ExtractionResult:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        if response.error.message:
            raise RuntimeError(f"Cloud Vision error: {response.error.message}")

        text = response.full_text_annotation.text if response.full_text_annotation else ""
        return parse_text(text, self.name, self.model)
