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


class OpenAIExtractor:
    """OpenAI GPT vision extraction (JSON mode with a strict schema).

    PDFs are not directly supported by the chat image input, so this provider
    targets image documents; route PDFs through ``claude`` or ``google_vision``.
    """

    name = "openai"

    def __init__(self) -> None:
        self.model = settings.openai_model

    def extract(self, content: bytes, mime_type: str, filename: str) -> ExtractionResult:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        b64 = base64.standard_b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type or 'image/png'};base64,{b64}"

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": OUTPUT_SCHEMA, "strict": True},
            },
        )
        data = json.loads(response.choices[0].message.content)
        return parse_payload(data, self.name, self.model)
