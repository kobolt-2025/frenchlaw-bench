"""LLM-as-Judge : evaluation de chaque critere de rubric."""

from __future__ import annotations

import asyncio
import json
import logging

from frenchlaw_bench.json_utils import parse_llm_json
from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.models.enums import Dimension
from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import RubricItem, Task
from frenchlaw_bench.scoring.prompts import (
    NEGATIF_ITEM_PROMPT,
    RUBRIC_ITEM_PROMPT,
    RUBRIC_JUDGE_SYSTEM,
)

logger = logging.getLogger(__name__)


async def judge_rubric_item(
    client: BaseLLMClient,
    task: Task,
    response: str,
    item: RubricItem,
) -> RubricItemResult:
    """Evalue un critere de rubric via LLM-as-judge avec extraction de preuves."""
    prompt = RUBRIC_ITEM_PROMPT.format(
        task_title=task.title,
        prompt=task.prompt,
        response=response,
        item_id=item.id,
        dimension=item.dimension.value,
        description=item.description,
        points=item.points,
    )

    llm_resp = await client.complete(prompt, system=RUBRIC_JUDGE_SYSTEM, temperature=0.0)

    try:
        data = parse_llm_json(llm_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de parser la reponse du juge pour %s", item.id)
        return RubricItemResult(
            item_id=item.id,
            satisfied=False,
            reasoning="Parse error",
            dimension=item.dimension.value,
        )

    return RubricItemResult(
        item_id=item.id,
        satisfied=data.get("satisfied", False),
        reasoning=data.get("reasoning", ""),
        evidence=data.get("evidence", []),
        confidence=data.get("confidence", 1.0),
        dimension=item.dimension.value,
    )


async def judge_negatif_item(
    client: BaseLLMClient,
    task: Task,
    response: str,
    item: RubricItem,
) -> RubricItemResult:
    """Evalue un critere Negatif du rubric (detection d'erreur specifique)."""
    prompt = NEGATIF_ITEM_PROMPT.format(
        task_title=task.title,
        prompt=task.prompt,
        response=response,
        item_id=item.id,
        description=item.description,
        points=item.points,
    )

    llm_resp = await client.complete(prompt, system=RUBRIC_JUDGE_SYSTEM, temperature=0.0)

    try:
        data = parse_llm_json(llm_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de parser la reponse du juge pour negatif %s", item.id)
        return RubricItemResult(
            item_id=item.id,
            satisfied=False,
            reasoning="Parse error",
            dimension=Dimension.NEGATIF.value,
        )

    return RubricItemResult(
        item_id=item.id,
        satisfied=data.get("triggered", False),  # satisfied=True means error IS present
        reasoning=data.get("reasoning", ""),
        evidence=data.get("evidence", []),
        confidence=data.get("confidence", 1.0),
        dimension=Dimension.NEGATIF.value,
    )


async def judge_all_items(
    client: BaseLLMClient,
    task: Task,
    response: str,
) -> list[RubricItemResult]:
    """Evalue tous les criteres positifs d'un rubric en parallele."""
    positive_items = [i for i in task.rubric.items if i.dimension != Dimension.NEGATIF]

    coros = [judge_rubric_item(client, task, response, item) for item in positive_items]
    results = await asyncio.gather(*coros, return_exceptions=True)

    final = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("Erreur evaluation rubric item: %s", r)
        else:
            final.append(r)
    return final


async def judge_negatif_items(
    client: BaseLLMClient,
    task: Task,
    response: str,
) -> list[RubricItemResult]:
    """Evalue tous les criteres Negatif d'un rubric en parallele."""
    negatif_items = [i for i in task.rubric.items if i.dimension == Dimension.NEGATIF]
    if not negatif_items:
        return []

    coros = [judge_negatif_item(client, task, response, item) for item in negatif_items]
    results = await asyncio.gather(*coros, return_exceptions=True)

    final = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("Erreur evaluation negatif item: %s", r)
        else:
            final.append(r)
    return final
