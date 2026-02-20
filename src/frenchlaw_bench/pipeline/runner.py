"""Orchestrateur principal du pipeline d'evaluation."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path

from frenchlaw_bench.config import DATA_DIR, JUDGE_MODEL, MAX_CONCURRENT
from frenchlaw_bench.documents.extractor import load_task_documents
from frenchlaw_bench.llm.openrouter import OpenRouterClient
from frenchlaw_bench.models.result import (
    BenchmarkRun,
    HallucinationDetail,
    RunMetadata,
    TaskResult,
)
from frenchlaw_bench.models.task import Task
from frenchlaw_bench.scoring.aggregator import _estimate_cost, aggregate_scores
from frenchlaw_bench.scoring.answer_scorer import (
    compute_answer_score_with_penalties,
    compute_dimension_scores,
    compute_negatif_penalty,
)
from frenchlaw_bench.scoring.hallucination_detector import detect_hallucinations
from frenchlaw_bench.scoring.judge import judge_all_items, judge_negatif_items
from frenchlaw_bench.scoring.source_scorer import compute_source_score

logger = logging.getLogger(__name__)


async def evaluate_task(
    task: Task,
    subject_client: OpenRouterClient,
    judge_client: OpenRouterClient,
    semaphore: asyncio.Semaphore,
) -> TaskResult:
    """Evalue une seule tache : appel LLM sujet -> juge -> negatif -> hallucination -> source."""
    async with semaphore:
        logger.info("Tache %d : %s (modele %s)", task.number, task.title, subject_client.model)

        task_start = time.monotonic()

        # Preparer le contexte documents
        doc_context = load_task_documents(task.documents)
        full_prompt = task.prompt
        if doc_context:
            full_prompt = f"{doc_context}\n\n---\n\n{task.prompt}"

        try:
            # 1. Appel au modele sujet
            subject_resp = await subject_client.complete(full_prompt, max_tokens=4096)
            response_text = subject_resp.content

            # 2. Evaluation des criteres positifs (en parallele)
            rubric_results = await judge_all_items(judge_client, task, response_text)

            # 3. Evaluation des criteres Negatif (en parallele)
            negatif_results = await judge_negatif_items(judge_client, task, response_text)

            # 4. Detection d'hallucinations (avec plafond = total points positifs)
            max_penalty = task.rubric.total_positive_points
            halluc = await detect_hallucinations(
                judge_client,
                response_text,
                task.title,
                source_context=doc_context or "Pas de documents source (tache knowledge-only)",
                max_penalty=max_penalty,
            )

            # 5. Source scoring
            src_score = await compute_source_score(judge_client, response_text)

            # 6. Calcul du score final avec toutes les penalites
            negatif_pen = compute_negatif_penalty(negatif_results, task.rubric)
            answer_score = compute_answer_score_with_penalties(
                task.rubric,
                rubric_results,
                hallucination_penalty=halluc.penalty_points,
                negatif_penalty=negatif_pen,
            )

            # 7. Scores par dimension
            dim_scores = compute_dimension_scores(task.rubric, rubric_results)

            # 8. Comptages
            rubric_satisfied = sum(1 for r in rubric_results if r.satisfied)
            negatif_triggered = sum(1 for r in negatif_results if r.satisfied)

            # 9. Cout
            cost = _estimate_cost(
                subject_client.model,
                subject_resp.input_tokens,
                subject_resp.output_tokens,
            )

            # Convertir les details hallucination
            halluc_details = [
                HallucinationDetail(
                    claim=d.claim,
                    hallucinated=d.hallucinated,
                    severity=d.severity,
                    category=d.category,
                    reasoning=d.reasoning,
                )
                for d in halluc.details
            ]

            elapsed = time.monotonic() - task_start

            return TaskResult(
                task_number=task.number,
                task_title=task.title,
                category=task.category.value,
                sub_category=task.sub_category.value,
                task_type=task.task_type.value,
                model_id=subject_client.model,
                response=response_text,
                rubric_results=rubric_results,
                negatif_results=negatif_results,
                answer_score=answer_score,
                answer_score_by_dimension=dim_scores,
                source_score=src_score,
                hallucination_rate=halluc.rate,
                hallucination_details=halluc_details,
                hallucination_penalty=halluc.penalty_points,
                hallucination_count=halluc.hallucinated_claims,
                hallucination_severity_counts=halluc.severity_counts,
                latency_seconds=elapsed,
                input_tokens=subject_resp.input_tokens,
                output_tokens=subject_resp.output_tokens,
                total_tokens=subject_resp.input_tokens + subject_resp.output_tokens,
                cost_usd=cost,
                rubric_items_satisfied=rubric_satisfied,
                rubric_items_total=len(rubric_results),
                negatif_items_triggered=negatif_triggered,
                negatif_items_total=len(negatif_results),
            )

        except Exception as e:
            elapsed = time.monotonic() - task_start
            logger.error("Erreur tache %d: %s", task.number, e)
            return TaskResult(
                task_number=task.number,
                task_title=task.title,
                category=task.category.value,
                sub_category=task.sub_category.value,
                task_type=task.task_type.value,
                model_id=subject_client.model,
                response="",
                error=str(e),
                latency_seconds=elapsed,
            )


async def run_benchmark(
    tasks: list[Task],
    model_ids: list[str],
    max_concurrent: int = MAX_CONCURRENT,
    tasks_csv_path: Path | None = None,
    judge_model: str | None = None,
    provider: str | None = None,
    quantization: str | None = None,
) -> BenchmarkRun:
    """Execute le benchmark complet sur les modeles donnes."""
    run_start = time.monotonic()
    semaphore = asyncio.Semaphore(max_concurrent)
    effective_judge = judge_model or JUDGE_MODEL
    judge_client = OpenRouterClient(model=effective_judge)

    all_results: list[TaskResult] = []
    failed_results: list[TaskResult] = []

    try:
        for model_id in model_ids:
            logger.info("=== Evaluation du modele : %s ===", model_id)
            subject_client = OpenRouterClient(
                model=model_id,
                provider=provider,
                quantization=quantization,
            )

            try:
                coros = [
                    evaluate_task(task, subject_client, judge_client, semaphore)
                    for task in tasks
                ]
                results = await asyncio.gather(*coros, return_exceptions=True)

                for r in results:
                    if isinstance(r, Exception):
                        logger.error("Erreur tache : %s", r)
                        failed_results.append(
                            TaskResult(
                                task_number=0,
                                model_id=model_id,
                                response="",
                                error=str(r),
                            )
                        )
                    elif r.error:
                        failed_results.append(r)
                        all_results.append(r)
                    else:
                        all_results.append(r)
            finally:
                await subject_client.close()
    finally:
        await judge_client.close()

    run_duration = time.monotonic() - run_start

    # Metadonnees
    csv_path = tasks_csv_path or (DATA_DIR / "core" / "tasks.csv")
    metadata = RunMetadata(
        timestamp_utc=datetime.now(),
        duration_seconds=run_duration,
        subject_models=model_ids,
        judge_model=effective_judge,
        judge_temperature=0.0,
        dataset_path=str(csv_path),
        dataset_sha256=RunMetadata.compute_dataset_hash(csv_path),
        n_tasks=len(tasks),
    )

    agg = aggregate_scores(tasks, all_results)

    return BenchmarkRun(
        run_id=uuid.uuid4().hex[:12],
        timestamp=datetime.now(),
        models=model_ids,
        metadata=metadata,
        task_results=all_results,
        failed_tasks=failed_results,
        aggregates=agg,
    )
