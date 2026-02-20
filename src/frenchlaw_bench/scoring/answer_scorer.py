"""Calcul de l'Answer Score à partir des résultats du juge."""

from __future__ import annotations

from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import Rubric


def compute_answer_score(rubric: Rubric, results: list[RubricItemResult]) -> float:
    """Calcule le score de réponse.

    Answer Score = (pts positifs gagnés + pénalités négatives) / total pts positifs disponibles

    Les items négatifs sont traités séparément par le hallucination detector.
    """
    total_positive = rubric.total_positive_points
    if total_positive == 0:
        return 0.0

    result_map = {r.item_id: r for r in results}
    points_earned = 0.0

    for item in rubric.items:
        if item.points <= 0:
            continue
        result = result_map.get(item.id)
        if result and result.satisfied:
            points_earned += item.points

    return points_earned / total_positive


def compute_answer_score_with_penalties(
    rubric: Rubric,
    results: list[RubricItemResult],
    hallucination_penalty: float = 0.0,
) -> float:
    """Calcule le score de réponse avec pénalités d'hallucination."""
    total_positive = rubric.total_positive_points
    if total_positive == 0:
        return 0.0

    result_map = {r.item_id: r for r in results}
    points_earned = 0.0

    for item in rubric.items:
        if item.points <= 0:
            continue
        result = result_map.get(item.id)
        if result and result.satisfied:
            points_earned += item.points

    score = (points_earned - hallucination_penalty) / total_positive
    return score
