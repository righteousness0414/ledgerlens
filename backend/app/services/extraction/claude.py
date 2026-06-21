from __future__ import annotations

import base64
import json

from app.config import get_settings
from app.services.extraction._prompt import (
    OUTPUT_SCHEMA,
    SYSTEM_PROMPT,
    USER_PROMPT,
    parse_payload,
)
from app.services.extraction.base import ExtractionResult

settings = get_settings()


class ClaudeExtractor:
    """Anthropic Claude vision extraction.

    Sends the document (image or PDF) to Claude with a strict JSON schema via
    ``output_config.format`` and adaptive thinking, per the claude-api skill.
    The model returns one {value, confidence} object per field plus line items.
    """

    name = "claude"

    def __init__(self) -> None:
        self.model = settings.claude_model

    def extract(self, content: bytes, mime_type: str, filename: str) -> ExtractionResult:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        b64 = base64.standard_b64encode(content).decode("utf-8")
        if mime_type == "application/pdf":
            source_block = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            }
        else:
            source_block = {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type or "image/png", "data": b64},
            }

        response = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            messages=[
                {"role": "user", "content": [source_block, {"type": "text", "text": USER_PROMPT}]}
            ],
        )

        text = next((b.text for b in response.content if b.type == "text"), "{}")
        data = json.loads(text)
        return parse_payload(data, self.name, self.model)
