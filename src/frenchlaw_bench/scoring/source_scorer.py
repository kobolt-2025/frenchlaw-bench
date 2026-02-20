"""Calcul du Source Score."""

from __future__ import annotations

import json
import logging

from frenchlaw_bench.json_utils import parse_llm_json
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
        data = parse_llm_json(llm_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de parser la réponse du source scorer")
        return None

    total = data.get("total_needing_source", 0)
    if total == 0:
        return None

    valid = data.get("total_with_valid_source", 0)
    return valid / total
