"""Calcul du Source Score."""

from __future__ import annotations

import json
import logging

from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.scoring.prompts import SOURCE_SCORE_PROMPT, SOURCE_SCORE_SYSTEM

logger = logging.getLogger(__name__)


async def compute_source_score(client: BaseLLMClient, response: str) -> float | None:
    """Calcule le Source Score via LLM.

    Source Score = assertions avec attribution valide / assertions nécessitant vérification

    Retourne None si aucune assertion ne nécessite de source.
    """
    prompt = SOURCE_SCORE_PROMPT.format(response=response)
    llm_resp = await client.complete(prompt, system=SOURCE_SCORE_SYSTEM, temperature=0.0)

    try:
        data = json.loads(llm_resp.content)
    except json.JSONDecodeError:
        cleaned = llm_resp.content.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(cleaned[start:end])
        else:
            logger.warning("Impossible de parser la réponse du source scorer")
            return None

    total = data.get("total_needing_source", 0)
    if total == 0:
        return None

    valid = data.get("total_with_valid_source", 0)
    return valid / total
