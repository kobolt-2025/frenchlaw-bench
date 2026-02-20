"""Agrégation des scores par modèle, catégorie et type de tâche."""

from __future__ import annotations

from collections import defaultdict

from frenchlaw_bench.models.result import AggregateScores, TaskResult
from frenchlaw_bench.models.task import Task


def aggregate_scores(
    tasks: list[Task],
    results: list[TaskResult],
) -> list[AggregateScores]:
    """Agrège les résultats par modèle."""
    task_map = {t.number: t for t in tasks}

    by_model: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_model[r.model_id].append(r)

    aggregates = []
    for model_id, model_results in by_model.items():
        by_category: dict[str, list[float]] = defaultdict(list)
        by_task_type: dict[str, list[float]] = defaultdict(list)
        all_scores = []
        source_scores = []
        hallucination_rates = []
        total_tokens = 0

        for r in model_results:
            task = task_map.get(r.task_number)
            if task is None:
                continue

            all_scores.append(r.answer_score)
            by_category[task.category.value].append(r.answer_score)
            by_task_type[task.task_type.value].append(r.answer_score)

            if r.source_score is not None:
                source_scores.append(r.source_score)
            if r.hallucination_rate is not None:
                hallucination_rates.append(r.hallucination_rate)

            total_tokens += r.input_tokens + r.output_tokens

        def _mean(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        aggregates.append(
            AggregateScores(
                model_id=model_id,
                answer_score_mean=_mean(all_scores),
                answer_score_by_category={k: _mean(v) for k, v in by_category.items()},
                answer_score_by_task_type={k: _mean(v) for k, v in by_task_type.items()},
                source_score_mean=_mean(source_scores) if source_scores else None,
                hallucination_rate_mean=_mean(hallucination_rates) if hallucination_rates else None,
                total_tasks=len(model_results),
                total_tokens=total_tokens,
            )
        )

    return aggregates
