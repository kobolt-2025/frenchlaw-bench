"""Calcul de l'Answer Score a partir des resultats du juge."""

from __future__ import annotations

from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import Rubric

# Poids par dimension (Substance et Methodologie ponderees plus haut,
# conformement aux meilleures pratiques des benchmarks juridiques).
DIMENSION_WEIGHTS: dict[str, float] = {
    "Structure": 1.0,
    "Style": 0.8,
    "Substance": 1.5,
    "Methodologie": 1.3,
}


def compute_answer_score(rubric: Rubric, results: list[RubricItemResult]) -> float:
    """Calcule le score de reponse simple (sans ponderations)."""
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


def compute_dimension_scores(
    rubric: Rubric,
    results: list[RubricItemResult],
) -> dict[str, float]:
    """Calcule le score par dimension (Structure, Style, Substance, Methodologie)."""
    result_map = {r.item_id: r for r in results}
    dimension_earned: dict[str, float] = {}
    dimension_total: dict[str, float] = {}

    for item in rubric.items:
        if item.points <= 0:
            continue
        dim = item.dimension.value
        dimension_total[dim] = dimension_total.get(dim, 0.0) + item.points
        result = result_map.get(item.id)
        if result and result.satisfied:
            dimension_earned[dim] = dimension_earned.get(dim, 0.0) + item.points

    scores = {}
    for dim, total in dimension_total.items():
        if total > 0:
            scores[dim] = dimension_earned.get(dim, 0.0) / total

    return scores


def compute_weighted_answer_score(
    rubric: Rubric,
    results: list[RubricItemResult],
    dimension_weights: dict[str, float] | None = None,
    use_confidence: bool = True,
) -> float:
    """Calcule le score de reponse pondere par dimension et confiance.

    - Les dimensions Substance et Methodologie pesent plus lourd.
    - La confiance du juge module les points gagnes (un "satisfied" a 0.6 de
      confiance ne rapporte que 60% des points).
    """
    weights = dimension_weights or DIMENSION_WEIGHTS
    result_map = {r.item_id: r for r in results}

    total_weighted = 0.0
    earned_weighted = 0.0

    for item in rubric.items:
        if item.points <= 0:
            continue
        w = weights.get(item.dimension.value, 1.0)
        total_weighted += item.points * w

        result = result_map.get(item.id)
        if result and result.satisfied:
            confidence_factor = result.confidence if use_confidence else 1.0
            earned_weighted += item.points * w * confidence_factor

    if total_weighted == 0:
        return 0.0

    return earned_weighted / total_weighted


def compute_answer_score_with_penalties(
    rubric: Rubric,
    results: list[RubricItemResult],
    hallucination_penalty: float = 0.0,
    negatif_penalty: float = 0.0,
    dimension_weights: dict[str, float] | None = None,
    use_confidence: bool = True,
) -> float:
    """Calcule le score final avec toutes les penalites.

    Score = max(0, (points ponderes gagnes - penalites) / total pondere)
    """
    weights = dimension_weights or DIMENSION_WEIGHTS
    result_map = {r.item_id: r for r in results}

    total_weighted = 0.0
    earned_weighted = 0.0

    for item in rubric.items:
        if item.points <= 0:
            continue
        w = weights.get(item.dimension.value, 1.0)
        total_weighted += item.points * w

        result = result_map.get(item.id)
        if result and result.satisfied:
            confidence_factor = result.confidence if use_confidence else 1.0
            earned_weighted += item.points * w * confidence_factor

    if total_weighted == 0:
        return 0.0

    total_penalty = hallucination_penalty + negatif_penalty
    score = (earned_weighted - total_penalty) / total_weighted

    # Clamp entre 0 et 1
    return max(0.0, min(1.0, score))


def compute_negatif_penalty(negatif_results: list[RubricItemResult], rubric: Rubric) -> float:
    """Calcule la penalite totale des items Negatif declenches.

    Utilise les points negatifs definis dans le rubric.
    """
    item_map = {i.id: i for i in rubric.items if i.points < 0}
    penalty = 0.0

    for result in negatif_results:
        if result.satisfied:  # satisfied=True pour Negatif = erreur detectee
            item = item_map.get(result.item_id)
            if item:
                penalty += abs(item.points)

    return penalty
