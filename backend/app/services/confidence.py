from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.services.extraction.base import ExtractionResult
from app.services.validation import FAIL, PASS, FieldCheck, validate

settings = get_settings()


@dataclass
class ScoredField:
    key: str
    value: str | None
    model_confidence: float
    validation_status: str
    validation_message: str | None
    final_confidence: float
    flagged: bool


def _combine(model_conf: float, check: FieldCheck) -> float:
    """final = model_confidence × validation_penalty, capped on failure.

    A passed (or n/a) check leaves the model's confidence intact. A failed check
    multiplies by ``validation_penalty`` and hard-caps at ``validation_fail_cap``
    so a confidently-wrong field can never look trustworthy.
    """
    if check.status == FAIL:
        penalized = model_conf * settings.validation_penalty
        return round(min(penalized, settings.validation_fail_cap), 4)
    return round(model_conf, 4)


def score(result: ExtractionResult) -> list[ScoredField]:
    values = {f.key: f.value for f in result.fields}
    checks = validate(values, result.line_items)

    scored: list[ScoredField] = []
    for field in result.fields:
        check = checks.get(field.key, FieldCheck("n/a"))
        final = _combine(field.confidence, check)
        scored.append(
            ScoredField(
                key=field.key,
                value=field.value,
                model_confidence=round(field.confidence, 4),
                validation_status=check.status,
                validation_message=check.message,
                final_confidence=final,
                flagged=final < settings.confidence_threshold,
            )
        )
    return scored
