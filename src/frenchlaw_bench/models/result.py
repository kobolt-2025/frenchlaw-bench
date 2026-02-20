"""Modèles pour les résultats d'évaluation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RubricItemResult(BaseModel):
    """Résultat d'évaluation d'un critère de rubric."""

    item_id: str
    satisfied: bool
    reasoning: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TaskResult(BaseModel):
    """Résultat d'évaluation d'une tâche pour un modèle."""

    task_number: int
    model_id: str
    response: str = Field(description="Réponse brute du LLM")
    rubric_results: list[RubricItemResult] = Field(default_factory=list)
    answer_score: float = Field(default=0.0, description="Score de réponse [peut être négatif, max 1.0]")
    source_score: float | None = Field(default=None, description="Score de sourcing [0-1]")
    hallucination_rate: float | None = Field(default=None, description="Taux d'hallucination [0-1]")
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class AggregateScores(BaseModel):
    """Scores agrégés pour un modèle sur l'ensemble du benchmark."""

    model_id: str
    answer_score_mean: float = 0.0
    answer_score_by_category: dict[str, float] = Field(default_factory=dict)
    answer_score_by_task_type: dict[str, float] = Field(default_factory=dict)
    source_score_mean: float | None = None
    hallucination_rate_mean: float | None = None
    total_tasks: int = 0
    total_tokens: int = 0


class BenchmarkRun(BaseModel):
    """Résultat complet d'une exécution du benchmark."""

    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    models: list[str]
    task_results: list[TaskResult] = Field(default_factory=list)
    aggregates: list[AggregateScores] = Field(default_factory=list)
