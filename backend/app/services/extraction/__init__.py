from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.extraction.base import Extractor

_PROVIDERS = {
    "mock": ("app.services.extraction.mock", "MockExtractor"),
    "claude": ("app.services.extraction.claude", "ClaudeExtractor"),
    "openai": ("app.services.extraction.openai", "OpenAIExtractor"),
    "google_vision": ("app.services.extraction.google_vision", "GoogleVisionExtractor"),
}


@lru_cache
def get_extractor(provider: str | None = None) -> Extractor:
    """Factory: select an extractor by name (defaults to EXTRACTION_PROVIDER).

    Providers are imported lazily so the optional SDK for an unused provider
    (anthropic / openai / google-cloud-vision) need not be installed.
    """
    name = (provider or get_settings().extraction_provider or "mock").lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown EXTRACTION_PROVIDER '{name}'. Options: {list(_PROVIDERS)}")
    module_path, cls_name = _PROVIDERS[name]
    module = __import__(module_path, fromlist=[cls_name])
    return getattr(module, cls_name)()
