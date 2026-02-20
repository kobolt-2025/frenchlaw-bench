"""Détecteur d'hallucinations en 2 étapes."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.scoring.prompts import (
    HALLUCINATION_EXTRACT_PROMPT,
    HALLUCINATION_EXTRACT_SYSTEM,
    HALLUCINATION_VERIFY_PROMPT,
    HALLUCINATION_VERIFY_SYSTEM,
)

logger = logging.getLogger(__name__)


@dataclass
class HallucinationResult:
    total_claims: int
    hallucinated_claims: int
    rate: float
    penalty_points: float
    details: list[dict]


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


async def detect_hallucinations(
    client: BaseLLMClient,
    response: str,
    task_title: str,
    source_context: str = "Pas de documents source (tâche knowledge-only)",
) -> HallucinationResult:
    """Pipeline de détection d'hallucinations en 2 étapes.

    1. Extraction des claims factuels
    2. Vérification de chaque claim
    """
    # Étape 1 : extraction
    extract_prompt = HALLUCINATION_EXTRACT_PROMPT.format(response=response)
    extract_resp = await client.complete(
        extract_prompt, system=HALLUCINATION_EXTRACT_SYSTEM, temperature=0.0
    )

    try:
        extract_data = _parse_json(extract_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de parser les claims extraits")
        return HallucinationResult(0, 0, 0.0, 0.0, [])

    claims = extract_data.get("claims", [])
    if not claims:
        return HallucinationResult(0, 0, 0.0, 0.0, [])

    # Étape 2 : vérification
    details = []
    hallucinated = 0

    for claim_data in claims:
        claim_text = claim_data.get("claim", "")
        if not claim_text:
            continue

        verify_prompt = HALLUCINATION_VERIFY_PROMPT.format(
            claim=claim_text,
            task_title=task_title,
            source_context=source_context,
        )
        verify_resp = await client.complete(
            verify_prompt, system=HALLUCINATION_VERIFY_SYSTEM, temperature=0.0
        )

        try:
            verify_data = _parse_json(verify_resp.content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Impossible de vérifier le claim: %s", claim_text[:50])
            continue

        is_hallucinated = verify_data.get("hallucinated", False)
        if is_hallucinated:
            hallucinated += 1

        details.append({
            "claim": claim_text,
            "hallucinated": is_hallucinated,
            "reasoning": verify_data.get("reasoning", ""),
        })

    total = len(details)
    rate = hallucinated / total if total > 0 else 0.0
    penalty = hallucinated * 1.0  # -1 pt par hallucination

    return HallucinationResult(
        total_claims=total,
        hallucinated_claims=hallucinated,
        rate=rate,
        penalty_points=penalty,
        details=details,
    )
