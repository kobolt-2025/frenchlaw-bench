"""Tests pour le scoring engine."""

from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import Rubric
from frenchlaw_bench.scoring.answer_scorer import (
    compute_answer_score,
    compute_answer_score_with_penalties,
)


def test_answer_score_perfect(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="ST1", satisfied=True),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=True),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="M1", satisfied=True),
    ]
    score = compute_answer_score(sample_rubric, results)
    assert score == 1.0


def test_answer_score_partial(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="ST1", satisfied=False),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=False),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="M1", satisfied=False),
    ]
    # Earned: S1(1) + SUB1(2) + SUB3(3) = 6 / total positive = 9
    score = compute_answer_score(sample_rubric, results)
    assert score == 6.0 / 9.0


def test_answer_score_zero(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=False),
        RubricItemResult(item_id="ST1", satisfied=False),
        RubricItemResult(item_id="SUB1", satisfied=False),
        RubricItemResult(item_id="SUB2", satisfied=False),
        RubricItemResult(item_id="SUB3", satisfied=False),
        RubricItemResult(item_id="M1", satisfied=False),
    ]
    score = compute_answer_score(sample_rubric, results)
    assert score == 0.0


def test_answer_score_with_penalties(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="ST1", satisfied=True),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=True),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="M1", satisfied=True),
    ]
    # All positive = 9, penalty = 3
    score = compute_answer_score_with_penalties(sample_rubric, results, hallucination_penalty=3.0)
    assert score == 6.0 / 9.0


def test_answer_score_negative_possible(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=False),
    ]
    # Earned: 0, penalty: 10 → (0 - 10) / 8 = negative
    score = compute_answer_score_with_penalties(sample_rubric, results, hallucination_penalty=10.0)
    assert score < 0.0
