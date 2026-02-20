"""Orchestrateur principal du pipeline d'évaluation."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from frenchlaw_bench.config import JUDGE_MODEL, MAX_CONCURRENT
from frenchlaw_bench.documents.extractor import load_task_documents
from frenchlaw_bench.llm.openrouter import OpenRouterClient
from frenchlaw_bench.models.result import BenchmarkRun, TaskResult
from frenchlaw_bench.models.task import Task
from frenchlaw_bench.scoring.aggregator import aggregate_scores
from frenchlaw_bench.scoring.answer_scorer import compute_answer_score_with_penalties
from frenchlaw_bench.scoring.hallucination_detector import detect_hallucinations
from frenchlaw_bench.scoring.judge import judge_all_items
from frenchlaw_bench.scoring.source_scorer import compute_source_score

logger = logging.getLogger(__name__)


async def evaluate_task(
    task: Task,
    subject_client: OpenRouterClient,
    judge_client: OpenRouterClient,
    semaphore: asyncio.Semaphore,
) -> TaskResult:
    """Évalue une seule tâche : appel LLM sujet → juge → hallucination → source."""
    async with semaphore:
        logger.info("Tâche %d : %s (modèle %s)", task.number, task.title, subject_client.model)

        # Préparer le contexte documents
        doc_context = load_task_documents(task.documents)
        full_prompt = task.prompt
        if doc_context:
            full_prompt = f"{doc_context}\n\n---\n\n{task.prompt}"

        # 1. Appel au modèle sujet
        subject_resp = await subject_client.complete(full_prompt, max_tokens=4096)
        response_text = subject_resp.content

        # 2. Évaluation par le juge (critères du rubric)
        rubric_results = await judge_all_items(judge_client, task, response_text)

        # 3. Détection d'hallucinations
        halluc = await detect_hallucinations(
            judge_client, response_text, task.title
        )

        # 4. Source scoring
        src_score = await compute_source_score(judge_client, response_text)

        # 5. Calcul du score final
        answer_score = compute_answer_score_with_penalties(
            task.rubric, rubric_results, halluc.penalty_points
        )

        return TaskResult(
            task_number=task.number,
            model_id=subject_client.model,
            response=response_text,
            rubric_results=rubric_results,
            answer_score=answer_score,
            source_score=src_score,
            hallucination_rate=halluc.rate,
            latency_seconds=subject_resp.latency_seconds,
            input_tokens=subject_resp.input_tokens,
            output_tokens=subject_resp.output_tokens,
        )


async def run_benchmark(
    tasks: list[Task],
    model_ids: list[str],
    max_concurrent: int = MAX_CONCURRENT,
) -> BenchmarkRun:
    """Exécute le benchmark complet sur les modèles donnés."""
    semaphore = asyncio.Semaphore(max_concurrent)
    judge_client = OpenRouterClient(model=JUDGE_MODEL)

    all_results: list[TaskResult] = []

    try:
        for model_id in model_ids:
            logger.info("=== Évaluation du modèle : %s ===", model_id)
            subject_client = OpenRouterClient(model=model_id)

            try:
                coros = [
                    evaluate_task(task, subject_client, judge_client, semaphore)
                    for task in tasks
                ]
                results = await asyncio.gather(*coros, return_exceptions=True)

                for r in results:
                    if isinstance(r, Exception):
                        logger.error("Erreur tâche : %s", r)
                    else:
                        all_results.append(r)
            finally:
                await subject_client.close()
    finally:
        await judge_client.close()

    agg = aggregate_scores(tasks, all_results)

    return BenchmarkRun(
        run_id=uuid.uuid4().hex[:12],
        timestamp=datetime.now(),
        models=model_ids,
        task_results=all_results,
        aggregates=agg,
    )
