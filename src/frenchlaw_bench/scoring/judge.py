"""LLM-as-Judge : évaluation de chaque critère de rubric."""

from __future__ import annotations

import json
import logging

from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import RubricItem, Task
from frenchlaw_bench.scoring.prompts import RUBRIC_ITEM_PROMPT, RUBRIC_JUDGE_SYSTEM

logger = logging.getLogger(__name__)


async def judge_rubric_item(
    client: BaseLLMClient,
    task: Task,
    response: str,
    item: RubricItem,
) -> RubricItemResult:
    """Évalue un critère de rubric via LLM-as-judge."""
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
        data = json.loads(llm_resp.content)
    except json.JSONDecodeError:
        cleaned = llm_resp.content.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(cleaned[start:end])
        else:
            logger.warning("Impossible de parser la réponse du juge pour %s", item.id)
            return RubricItemResult(item_id=item.id, satisfied=False, reasoning="Parse error")

    return RubricItemResult(
        item_id=item.id,
        satisfied=data.get("satisfied", False),
        reasoning=data.get("reasoning", ""),
        confidence=data.get("confidence", 1.0),
    )


async def judge_all_items(
    client: BaseLLMClient,
    task: Task,
    response: str,
) -> list[RubricItemResult]:
    """Évalue tous les critères d'un rubric."""
    results = []
    for item in task.rubric.items:
        if item.dimension.value == "Négatif":
            continue
        result = await judge_rubric_item(client, task, response, item)
        results.append(result)
    return results
