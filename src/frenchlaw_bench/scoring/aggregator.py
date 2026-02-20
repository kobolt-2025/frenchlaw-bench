"""Agregation des scores par modele, categorie et type de tache."""

from __future__ import annotations

import math
import random
from collections import defaultdict

from frenchlaw_bench.models.result import AggregateScores, LatencyStats, TaskResult, TokenStats
from frenchlaw_bench.models.task import Task

# Estimation de couts OpenRouter (USD par token) — configurable
MODEL_PRICING: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-20250514": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "anthropic/claude-sonnet-4": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "anthropic/claude-haiku-3.5": {"input": 0.80 / 1_000_000, "output": 4.0 / 1_000_000},
    "openai/gpt-4o": {"input": 2.5 / 1_000_000, "output": 10.0 / 1_000_000},
    "openai/gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "google/gemini-2.5-pro": {"input": 1.25 / 1_000_000, "output": 10.0 / 1_000_000},
    "google/gemini-2.5-flash": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.40 / 1_000_000, "output": 0.40 / 1_000_000},
    "mistralai/mistral-large-2411": {"input": 2.0 / 1_000_000, "output": 6.0 / 1_000_000},
    "deepseek/deepseek-chat-v3-0324": {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000},
}

# Fallback pour modeles inconnus
_DEFAULT_PRICING = {"input": 2.0 / 1_000_000, "output": 8.0 / 1_000_000}


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estime le cout en USD pour un appel."""
    pricing = MODEL_PRICING.get(model_id, _DEFAULT_PRICING)
    return input_tokens * pricing["input"] + output_tokens * pricing["output"]


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _bootstrap_ci(
    vals: list[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Intervalle de confiance par bootstrap."""
    if len(vals) < 2:
        m = _mean(vals)
        return m, m

    rng = random.Random(seed)
    boot_means = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(vals) for _ in range(len(vals))]
        boot_means.append(_mean(sample))

    boot_means.sort()
    alpha = (1 - confidence) / 2
    lower_idx = max(0, int(alpha * n_bootstrap))
    upper_idx = min(n_bootstrap - 1, int((1 - alpha) * n_bootstrap))
    return boot_means[lower_idx], boot_means[upper_idx]


def _compute_latency_stats(latencies: list[float]) -> LatencyStats:
    if not latencies:
        return LatencyStats()
    return LatencyStats(
        mean=_mean(latencies),
        median=_median(latencies),
        p50=_percentile(latencies, 50),
        p95=_percentile(latencies, 95),
        p99=_percentile(latencies, 99),
        min=min(latencies),
        max=max(latencies),
        std=_std(latencies),
    )


def _compute_token_stats(results: list[TaskResult]) -> TokenStats:
    if not results:
        return TokenStats()
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total = total_input + total_output
    n = len(results)
    return TokenStats(
        total_input=total_input,
        total_output=total_output,
        total=total,
        mean_input_per_task=total_input / n,
        mean_output_per_task=total_output / n,
        mean_total_per_task=total / n,
    )


def aggregate_scores(
    tasks: list[Task],
    results: list[TaskResult],
) -> list[AggregateScores]:
    """Agrege les resultats par modele avec statistiques completes."""
    task_map = {t.number: t for t in tasks}

    by_model: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_model[r.model_id].append(r)

    aggregates = []
    for model_id, model_results in by_model.items():
        by_category: dict[str, list[float]] = defaultdict(list)
        by_sub_category: dict[str, list[float]] = defaultdict(list)
        by_task_type: dict[str, list[float]] = defaultdict(list)
        by_dimension: dict[str, list[float]] = defaultdict(list)
        all_scores: list[float] = []
        source_scores: list[float] = []
        hallucination_rates: list[float] = []
        latencies: list[float] = []
        total_cost = 0.0
        halluc_total = 0
        halluc_severity: dict[str, int] = {"critical": 0, "major": 0, "minor": 0}
        tasks_with_halluc = 0
        tasks_succeeded = 0
        tasks_failed = 0
        rubric_satisfied_total = 0
        rubric_total = 0
        negatif_triggered_total = 0
        negatif_total = 0

        for r in model_results:
            task = task_map.get(r.task_number)
            if task is None:
                continue

            # Succes/echec
            if r.error:
                tasks_failed += 1
                continue
            tasks_succeeded += 1

            all_scores.append(r.answer_score)
            by_category[task.category.value].append(r.answer_score)
            by_sub_category[task.sub_category.value].append(r.answer_score)
            by_task_type[task.task_type.value].append(r.answer_score)
            latencies.append(r.latency_seconds)

            # Scores par dimension
            for dim, score in r.answer_score_by_dimension.items():
                by_dimension[dim].append(score)

            # Source
            if r.source_score is not None:
                source_scores.append(r.source_score)

            # Hallucinations
            if r.hallucination_rate is not None:
                hallucination_rates.append(r.hallucination_rate)
            halluc_total += r.hallucination_count
            if r.hallucination_count > 0:
                tasks_with_halluc += 1
            for sev, count in r.hallucination_severity_counts.items():
                halluc_severity[sev] = halluc_severity.get(sev, 0) + count

            # Comptages rubric
            rubric_satisfied_total += r.rubric_items_satisfied
            rubric_total += r.rubric_items_total
            negatif_triggered_total += r.negatif_items_triggered
            negatif_total += r.negatif_items_total

            # Cout
            total_cost += r.cost_usd

        # Intervalles de confiance
        ci_lower, ci_upper = _bootstrap_ci(all_scores) if all_scores else (0.0, 0.0)

        total_tokens_val = sum(
            r.input_tokens + r.output_tokens for r in model_results if not r.error
        )

        aggregates.append(
            AggregateScores(
                model_id=model_id,
                # Scores
                answer_score_mean=_mean(all_scores),
                answer_score_median=_median(all_scores),
                answer_score_std=_std(all_scores),
                answer_score_min=min(all_scores) if all_scores else 0.0,
                answer_score_max=max(all_scores) if all_scores else 0.0,
                answer_score_ci_lower=ci_lower,
                answer_score_ci_upper=ci_upper,
                # Ventilations
                answer_score_by_category={k: _mean(v) for k, v in by_category.items()},
                answer_score_by_task_type={k: _mean(v) for k, v in by_task_type.items()},
                answer_score_by_dimension={k: _mean(v) for k, v in by_dimension.items()},
                answer_score_by_sub_category={k: _mean(v) for k, v in by_sub_category.items()},
                # Source
                source_score_mean=_mean(source_scores) if source_scores else None,
                source_score_std=_std(source_scores) if len(source_scores) >= 2 else None,
                # Hallucinations
                hallucination_rate_mean=(
                    _mean(hallucination_rates) if hallucination_rates else None
                ),
                hallucination_total_count=halluc_total,
                hallucination_severity_counts=halluc_severity,
                tasks_with_hallucinations=tasks_with_halluc,
                # Comptages
                total_tasks=len(model_results),
                tasks_succeeded=tasks_succeeded,
                tasks_failed=tasks_failed,
                rubric_items_satisfied_total=rubric_satisfied_total,
                rubric_items_total=rubric_total,
                rubric_satisfaction_rate=(
                    rubric_satisfied_total / rubric_total if rubric_total > 0 else 0.0
                ),
                negatif_items_triggered_total=negatif_triggered_total,
                negatif_items_total=negatif_total,
                # Latence
                latency=_compute_latency_stats(latencies),
                # Tokens
                tokens=_compute_token_stats(
                    [r for r in model_results if not r.error]
                ),
                # Cout
                cost_total_usd=total_cost,
                cost_per_task_usd=total_cost / tasks_succeeded if tasks_succeeded > 0 else 0.0,
                # Compat
                total_tokens=total_tokens_val,
            )
        )

    return aggregates
