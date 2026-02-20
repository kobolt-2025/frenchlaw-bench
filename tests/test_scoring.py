"""Tests pour le scoring engine."""

from frenchlaw_bench.models.result import RubricItemResult
from frenchlaw_bench.models.task import Rubric
from frenchlaw_bench.scoring.answer_scorer import (
    compute_answer_score,
    compute_answer_score_with_penalties,
)


def test_answer_score_perfect(sample_rubric: Rubric) -> None:
    # sample_rubric has: S1(1) S2(1) ST1(1) SUB1(2) SUB2(1) SUB3(3) SUB4(1) M1(1) = 11 pts
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="S2", satisfied=True),
        RubricItemResult(item_id="ST1", satisfied=True),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=True),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="SUB4", satisfied=True),
        RubricItemResult(item_id="M1", satisfied=True),
    ]
    score = compute_answer_score(sample_rubric, results)
    assert score == 1.0


def test_answer_score_partial(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="S2", satisfied=False),
        RubricItemResult(item_id="ST1", satisfied=False),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=False),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="SUB4", satisfied=False),
        RubricItemResult(item_id="M1", satisfied=False),
    ]
    # Earned: S1(1) + SUB1(2) + SUB3(3) = 6 / total positive = 11
    score = compute_answer_score(sample_rubric, results)
    assert abs(score - 6.0 / 11.0) < 0.001


def test_answer_score_zero(sample_rubric: Rubric) -> None:
    results = [
        RubricItemResult(item_id="S1", satisfied=False),
        RubricItemResult(item_id="S2", satisfied=False),
        RubricItemResult(item_id="ST1", satisfied=False),
        RubricItemResult(item_id="SUB1", satisfied=False),
        RubricItemResult(item_id="SUB2", satisfied=False),
        RubricItemResult(item_id="SUB3", satisfied=False),
        RubricItemResult(item_id="SUB4", satisfied=False),
        RubricItemResult(item_id="M1", satisfied=False),
    ]
    score = compute_answer_score(sample_rubric, results)
    assert score == 0.0


def test_answer_score_with_penalties_clamped(sample_rubric: Rubric) -> None:
    """Score with huge penalty should be clamped to 0."""
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
    ]
    score = compute_answer_score_with_penalties(
        sample_rubric, results, hallucination_penalty=100.0
    )
    assert score == 0.0


def test_answer_score_with_penalties(sample_rubric: Rubric) -> None:
    """Penalty reduces the score."""
    results = [
        RubricItemResult(item_id="S1", satisfied=True),
        RubricItemResult(item_id="S2", satisfied=True),
        RubricItemResult(item_id="ST1", satisfied=True),
        RubricItemResult(item_id="SUB1", satisfied=True),
        RubricItemResult(item_id="SUB2", satisfied=True),
        RubricItemResult(item_id="SUB3", satisfied=True),
        RubricItemResult(item_id="SUB4", satisfied=True),
        RubricItemResult(item_id="M1", satisfied=True),
    ]
    score_no_penalty = compute_answer_score_with_penalties(sample_rubric, results)
    score_with_penalty = compute_answer_score_with_penalties(
        sample_rubric, results, hallucination_penalty=3.0
    )
    assert score_with_penalty < score_no_penalty
    assert score_with_penalty >= 0.0
