"""Tests pour le pipeline (chargement et agregation, sans appels LLM)."""

from frenchlaw_bench.models.enums import Category, Dimension, SubCategory, TaskType
from frenchlaw_bench.models.result import AggregateScores, RubricItemResult, TaskResult
from frenchlaw_bench.models.task import Rubric, RubricItem, Task
from frenchlaw_bench.scoring.aggregator import (
    _bootstrap_ci,
    _mean,
    _median,
    _percentile,
    _std,
    aggregate_scores,
)
from frenchlaw_bench.scoring.answer_scorer import (
    DIMENSION_WEIGHTS,
    compute_answer_score,
    compute_answer_score_with_penalties,
    compute_dimension_scores,
    compute_negatif_penalty,
    compute_weighted_answer_score,
)


def _make_task(number: int, category: Category, task_type: TaskType) -> Task:
    return Task(
        number=number,
        category=category,
        sub_category=SubCategory.CONTRATS,
        task_type=task_type,
        title=f"Tache {number}",
        prompt="Prompt test",
        rubric=Rubric(
            items=[
                RubricItem(id="S1", dimension=Dimension.STRUCTURE, description="test", points=1),
                RubricItem(id="SUB1", dimension=Dimension.SUBSTANCE, description="test", points=2),
                RubricItem(id="N1", dimension=Dimension.NEGATIF, description="halluc", points=-1),
            ]
        ),
    )


def _make_result(
    task_number: int,
    model_id: str,
    answer_score: float,
    latency: float = 5.0,
    input_tokens: int = 1000,
    output_tokens: int = 500,
    halluc_count: int = 0,
    cost: float = 0.01,
) -> TaskResult:
    return TaskResult(
        task_number=task_number,
        model_id=model_id,
        response="r",
        answer_score=answer_score,
        latency_seconds=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        hallucination_count=halluc_count,
        hallucination_rate=halluc_count / 10 if halluc_count else 0.0,
        hallucination_severity_counts={"critical": halluc_count, "major": 0, "minor": 0},
        cost_usd=cost,
        rubric_items_satisfied=1,
        rubric_items_total=2,
        negatif_items_triggered=0,
        negatif_items_total=1,
        answer_score_by_dimension={"Structure": 1.0, "Substance": answer_score},
    )


# ===== Aggregation tests =====


def test_aggregate_single_model() -> None:
    tasks = [
        _make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE),
        _make_task(2, Category.CONTENTIEUX, TaskType.REDACTION),
    ]
    results = [
        _make_result(1, "test-model", 0.8),
        _make_result(2, "test-model", 0.6),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 1
    assert aggs[0].model_id == "test-model"
    assert abs(aggs[0].answer_score_mean - 0.7) < 0.001
    assert aggs[0].total_tasks == 2
    assert aggs[0].tasks_succeeded == 2
    assert aggs[0].tasks_failed == 0


def test_aggregate_multiple_models() -> None:
    tasks = [_make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE)]
    results = [
        _make_result(1, "model-a", 0.9),
        _make_result(1, "model-b", 0.5),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 2
    ids = {a.model_id for a in aggs}
    assert ids == {"model-a", "model-b"}


def test_aggregate_by_category() -> None:
    tasks = [
        _make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE),
        _make_task(2, Category.DROIT_PRIVE, TaskType.REDACTION),
        _make_task(3, Category.DROIT_EUROPEEN, TaskType.RECHERCHE_JURIDIQUE),
    ]
    results = [
        _make_result(1, "m", 0.8),
        _make_result(2, "m", 0.6),
        _make_result(3, "m", 1.0),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 1
    agg = aggs[0]
    assert abs(agg.answer_score_by_category["Droit Privé"] - 0.7) < 0.001
    assert abs(agg.answer_score_by_category["Droit Européen"] - 1.0) < 0.001


def test_aggregate_confidence_intervals() -> None:
    tasks = [_make_task(i, Category.DROIT_PRIVE, TaskType.REDACTION) for i in range(1, 6)]
    results = [_make_result(i, "m", score) for i, score in zip(range(1, 6), [0.5, 0.6, 0.7, 0.8, 0.9])]
    aggs = aggregate_scores(tasks, results)
    agg = aggs[0]
    assert abs(agg.answer_score_mean - 0.7) < 0.001
    assert agg.answer_score_ci_lower < agg.answer_score_mean
    assert agg.answer_score_ci_upper > agg.answer_score_mean
    assert agg.answer_score_ci_lower > 0
    assert agg.answer_score_ci_upper <= 1.0


def test_aggregate_latency_stats() -> None:
    tasks = [_make_task(i, Category.DROIT_PRIVE, TaskType.REDACTION) for i in range(1, 4)]
    results = [
        _make_result(1, "m", 0.5, latency=2.0),
        _make_result(2, "m", 0.5, latency=5.0),
        _make_result(3, "m", 0.5, latency=10.0),
    ]
    aggs = aggregate_scores(tasks, results)
    lat = aggs[0].latency
    assert lat.min == 2.0
    assert lat.max == 10.0
    assert lat.p50 == 5.0  # median


def test_aggregate_token_stats() -> None:
    tasks = [_make_task(1, Category.DROIT_PRIVE, TaskType.REDACTION)]
    results = [_make_result(1, "m", 0.5, input_tokens=1000, output_tokens=500)]
    aggs = aggregate_scores(tasks, results)
    tok = aggs[0].tokens
    assert tok.total_input == 1000
    assert tok.total_output == 500
    assert tok.total == 1500
    assert tok.mean_total_per_task == 1500.0


def test_aggregate_cost() -> None:
    tasks = [_make_task(i, Category.DROIT_PRIVE, TaskType.REDACTION) for i in range(1, 3)]
    results = [
        _make_result(1, "m", 0.5, cost=0.10),
        _make_result(2, "m", 0.5, cost=0.20),
    ]
    aggs = aggregate_scores(tasks, results)
    assert abs(aggs[0].cost_total_usd - 0.30) < 0.001
    assert abs(aggs[0].cost_per_task_usd - 0.15) < 0.001


def test_aggregate_hallucination_stats() -> None:
    tasks = [_make_task(i, Category.DROIT_PRIVE, TaskType.REDACTION) for i in range(1, 3)]
    results = [
        _make_result(1, "m", 0.5, halluc_count=2),
        _make_result(2, "m", 0.5, halluc_count=0),
    ]
    aggs = aggregate_scores(tasks, results)
    assert aggs[0].hallucination_total_count == 2
    assert aggs[0].tasks_with_hallucinations == 1
    assert aggs[0].hallucination_severity_counts["critical"] == 2


def test_aggregate_rubric_counts() -> None:
    tasks = [_make_task(1, Category.DROIT_PRIVE, TaskType.REDACTION)]
    results = [_make_result(1, "m", 0.5)]
    aggs = aggregate_scores(tasks, results)
    assert aggs[0].rubric_items_satisfied_total == 1
    assert aggs[0].rubric_items_total == 2
    assert abs(aggs[0].rubric_satisfaction_rate - 0.5) < 0.001


def test_aggregate_failed_tasks() -> None:
    tasks = [_make_task(1, Category.DROIT_PRIVE, TaskType.REDACTION)]
    results = [
        TaskResult(task_number=1, model_id="m", response="", error="API error"),
    ]
    aggs = aggregate_scores(tasks, results)
    assert aggs[0].tasks_failed == 1
    assert aggs[0].tasks_succeeded == 0


# ===== Helper function tests =====


def test_mean() -> None:
    assert _mean([1.0, 2.0, 3.0]) == 2.0
    assert _mean([]) == 0.0


def test_median() -> None:
    assert _median([1.0, 2.0, 3.0]) == 2.0
    assert _median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert _median([]) == 0.0


def test_std() -> None:
    assert _std([1.0]) == 0.0
    assert _std([]) == 0.0
    result = _std([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert abs(result - 2.138) < 0.01


def test_percentile() -> None:
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(vals, 50) == 3.0
    assert _percentile(vals, 0) == 1.0
    assert _percentile(vals, 100) == 5.0


def test_bootstrap_ci() -> None:
    vals = [0.5, 0.6, 0.7, 0.8, 0.9]
    lower, upper = _bootstrap_ci(vals)
    assert lower < 0.7
    assert upper > 0.7
    # Single value
    lower, upper = _bootstrap_ci([0.5])
    assert lower == upper == 0.5


# ===== Answer scorer tests =====


def test_compute_answer_score(sample_rubric: "Rubric") -> None:
    from frenchlaw_bench.models.task import Rubric

    results = [
        RubricItemResult(item_id="S1", satisfied=True, reasoning="ok", confidence=1.0),
        RubricItemResult(item_id="S2", satisfied=True, reasoning="ok", confidence=1.0),
        RubricItemResult(item_id="ST1", satisfied=False, reasoning="no", confidence=0.9),
        RubricItemResult(item_id="SUB1", satisfied=True, reasoning="ok", confidence=0.8),
        RubricItemResult(item_id="SUB2", satisfied=True, reasoning="ok", confidence=1.0),
        RubricItemResult(item_id="SUB3", satisfied=False, reasoning="no", confidence=0.7),
        RubricItemResult(item_id="SUB4", satisfied=True, reasoning="ok", confidence=1.0),
        RubricItemResult(item_id="M1", satisfied=True, reasoning="ok", confidence=1.0),
    ]
    # Total positive = 1+1+1+2+1+3+1+1 = 11
    # Earned = 1+1+0+2+1+0+1+1 = 7
    score = compute_answer_score(sample_rubric, results)
    assert abs(score - 7 / 11) < 0.001


def test_compute_dimension_scores(sample_rubric: "Rubric") -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="S2", satisfied=False, reasoning="", confidence=1.0),
        RubricItemResult(item_id="ST1", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB1", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB2", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB3", satisfied=False, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB4", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="M1", satisfied=True, reasoning="", confidence=1.0),
    ]
    dims = compute_dimension_scores(sample_rubric, results)
    assert abs(dims["Structure"] - 0.5) < 0.001  # 1/2
    assert abs(dims["Style"] - 1.0) < 0.001  # 1/1
    assert abs(dims["Substance"] - 4 / 7) < 0.001  # (2+1+1)/7
    assert abs(dims["Méthodologie"] - 1.0) < 0.001  # 1/1


def test_weighted_answer_score(sample_rubric: "Rubric") -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="S2", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="ST1", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB1", satisfied=True, reasoning="", confidence=0.5),
        RubricItemResult(item_id="SUB2", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB3", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="SUB4", satisfied=True, reasoning="", confidence=1.0),
        RubricItemResult(item_id="M1", satisfied=True, reasoning="", confidence=1.0),
    ]
    # With confidence, SUB1 (2pts*1.5*0.5) = 1.5 instead of 3.0
    score_with_conf = compute_weighted_answer_score(sample_rubric, results, use_confidence=True)
    score_no_conf = compute_weighted_answer_score(sample_rubric, results, use_confidence=False)
    assert score_with_conf < score_no_conf


def test_score_with_penalties_clamped(sample_rubric: "Rubric") -> None:
    """Score should be clamped to [0, 1]."""
    results = [
        RubricItemResult(item_id="S1", satisfied=True, reasoning="", confidence=1.0),
    ]
    # Huge penalty
    score = compute_answer_score_with_penalties(
        sample_rubric, results, hallucination_penalty=100.0
    )
    assert score == 0.0

    # No penalty, all satisfied
    all_results = [
        RubricItemResult(item_id=f"id{i}", satisfied=True, reasoning="", confidence=1.0)
        for i, item in enumerate(sample_rubric.items)
        if item.points > 0
    ]
    # Fix IDs to match rubric
    for r, item in zip(all_results, [i for i in sample_rubric.items if i.points > 0]):
        r.item_id = item.id
    score = compute_answer_score_with_penalties(sample_rubric, all_results)
    assert score <= 1.0


def test_negatif_penalty(sample_rubric: "Rubric") -> None:
    # N1 triggered (-1pt), N2 not triggered
    negatif_results = [
        RubricItemResult(item_id="N1", satisfied=True, reasoning="halluc found", confidence=0.9),
        RubricItemResult(item_id="N2", satisfied=False, reasoning="ok", confidence=0.8),
    ]
    penalty = compute_negatif_penalty(negatif_results, sample_rubric)
    assert abs(penalty - 1.0) < 0.001  # Only N1 = 1pt

    # Both triggered
    negatif_results[1].satisfied = True
    penalty = compute_negatif_penalty(negatif_results, sample_rubric)
    assert abs(penalty - 1.5) < 0.001  # N1=1 + N2=0.5


# ===== CSV loading =====


def test_load_tasks_from_csv() -> None:
    """Test que le CSV des taches se charge correctement."""
    from frenchlaw_bench.core.loader import load_tasks

    tasks = load_tasks()
    assert len(tasks) == 20

    categories = {t.category for t in tasks}
    assert Category.DROIT_PRIVE in categories
    assert Category.CONTENTIEUX in categories
    assert Category.DROIT_EUROPEEN in categories

    prive_count = sum(1 for t in tasks if t.category == Category.DROIT_PRIVE)
    contentieux_count = sum(1 for t in tasks if t.category == Category.CONTENTIEUX)
    europeen_count = sum(1 for t in tasks if t.category == Category.DROIT_EUROPEEN)
    assert prive_count == 8
    assert contentieux_count == 7
    assert europeen_count == 5

    for task in tasks:
        assert task.rubric.total_positive_points > 0
        assert len(task.rubric.items) >= 8
        assert task.prompt.strip()
        # Verify negatif items exist
        negatif_items = [i for i in task.rubric.items if i.dimension.value == "Négatif"]
        assert len(negatif_items) >= 2, f"Task {task.number} should have negatif items"


# ===== Rubric parser =====


def test_rubric_parser(sample_rubric_text: str) -> None:
    from frenchlaw_bench.core.rubric_parser import parse_rubric

    rubric = parse_rubric(sample_rubric_text)
    assert rubric.total_positive_points == 11  # 1+1+1+2+1+3+1+1
    assert len(rubric.items) == 10
    assert len(rubric.negatif_items) == 2
    assert rubric.negatif_items[0].points == -1
    assert rubric.negatif_items[1].points == -0.5


# ===== Hallucination severity =====


def test_hallucination_severity_penalties() -> None:
    from frenchlaw_bench.scoring.hallucination_detector import SEVERITY_PENALTIES

    assert SEVERITY_PENALTIES["critical"] > SEVERITY_PENALTIES["major"]
    assert SEVERITY_PENALTIES["major"] > SEVERITY_PENALTIES["minor"]
    assert SEVERITY_PENALTIES["critical"] == 2.0
    assert SEVERITY_PENALTIES["major"] == 1.0
    assert SEVERITY_PENALTIES["minor"] == 0.3
