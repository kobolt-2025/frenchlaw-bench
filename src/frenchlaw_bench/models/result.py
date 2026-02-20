"""Modeles pour les resultats d'evaluation."""

from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RubricItemResult(BaseModel):
    """Resultat d'evaluation d'un critere de rubric."""

    item_id: str
    satisfied: bool
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list, description="Passages verbatim extraits")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    dimension: str = ""


class HallucinationDetail(BaseModel):
    """Detail d'un claim verifie lors de la detection d'hallucinations."""

    claim: str
    hallucinated: bool
    severity: str = Field(default="minor", description="critical | major | minor")
    category: str = Field(default="", description="citation_fabricated | article_wrong | etc.")
    reasoning: str = ""


class TaskResult(BaseModel):
    """Resultat d'evaluation d'une tache pour un modele."""

    task_number: int
    task_title: str = ""
    category: str = ""
    sub_category: str = ""
    task_type: str = ""
    model_id: str
    response: str = Field(description="Reponse brute du LLM")
    rubric_results: list[RubricItemResult] = Field(default_factory=list)
    negatif_results: list[RubricItemResult] = Field(
        default_factory=list, description="Resultats des items Negatif du rubric"
    )
    answer_score: float = Field(default=0.0, description="Score de reponse [0-1]")
    answer_score_by_dimension: dict[str, float] = Field(
        default_factory=dict, description="Score par dimension (Structure, Style, etc.)"
    )
    source_score: float | None = Field(default=None, description="Score de sourcing [0-1]")
    hallucination_rate: float | None = Field(default=None, description="Taux d'hallucination [0-1]")
    hallucination_details: list[HallucinationDetail] = Field(default_factory=list)
    hallucination_penalty: float = 0.0
    hallucination_count: int = 0
    hallucination_severity_counts: dict[str, int] = Field(
        default_factory=dict, description="Compte par severite: critical/major/minor"
    )
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = Field(default=None, description="Message d'erreur si la tache a echoue")
    retry_count: int = 0
    rubric_items_satisfied: int = 0
    rubric_items_total: int = 0
    negatif_items_triggered: int = 0
    negatif_items_total: int = 0


class LatencyStats(BaseModel):
    """Statistiques de latence."""

    mean: float = 0.0
    median: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std: float = 0.0


class TokenStats(BaseModel):
    """Statistiques de tokens."""

    total_input: int = 0
    total_output: int = 0
    total: int = 0
    mean_input_per_task: float = 0.0
    mean_output_per_task: float = 0.0
    mean_total_per_task: float = 0.0


class AggregateScores(BaseModel):
    """Scores agreges pour un modele sur l'ensemble du benchmark."""

    model_id: str

    # Scores avec intervalles de confiance
    answer_score_mean: float = 0.0
    answer_score_median: float = 0.0
    answer_score_std: float = 0.0
    answer_score_min: float = 0.0
    answer_score_max: float = 0.0
    answer_score_ci_lower: float = 0.0
    answer_score_ci_upper: float = 0.0

    # Ventilations
    answer_score_by_category: dict[str, float] = Field(default_factory=dict)
    answer_score_by_task_type: dict[str, float] = Field(default_factory=dict)
    answer_score_by_dimension: dict[str, float] = Field(default_factory=dict)
    answer_score_by_sub_category: dict[str, float] = Field(default_factory=dict)

    # Source scoring
    source_score_mean: float | None = None
    source_score_std: float | None = None

    # Hallucinations
    hallucination_rate_mean: float | None = None
    hallucination_total_count: int = 0
    hallucination_severity_counts: dict[str, int] = Field(default_factory=dict)
    tasks_with_hallucinations: int = 0

    # Comptages succes/echecs
    total_tasks: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    rubric_items_satisfied_total: int = 0
    rubric_items_total: int = 0
    rubric_satisfaction_rate: float = 0.0
    negatif_items_triggered_total: int = 0
    negatif_items_total: int = 0

    # Latence
    latency: LatencyStats = Field(default_factory=LatencyStats)

    # Tokens
    tokens: TokenStats = Field(default_factory=TokenStats)

    # Couts
    cost_total_usd: float = 0.0
    cost_per_task_usd: float = 0.0
    cost_judge_usd: float = 0.0

    # Anciens champs pour compat
    total_tokens: int = 0


class RunMetadata(BaseModel):
    """Metadonnees d'une execution du benchmark."""

    benchmark_version: str = "0.2.0"
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now())
    duration_seconds: float = 0.0

    # Modeles
    subject_models: list[str] = Field(default_factory=list)
    judge_model: str = ""
    judge_temperature: float = 0.0

    # Dataset
    dataset_path: str = ""
    dataset_sha256: str = ""
    n_tasks: int = 0

    # Environnement
    python_version: str = Field(default_factory=lambda: sys.version)
    platform: str = Field(default_factory=lambda: platform.platform())
    package_version: str = "0.2.0"

    @staticmethod
    def compute_dataset_hash(path: Path) -> str:
        """SHA256 du fichier de taches pour reproductibilite."""
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()


class BenchmarkRun(BaseModel):
    """Resultat complet d'une execution du benchmark."""

    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    models: list[str]
    metadata: RunMetadata = Field(default_factory=RunMetadata)
    task_results: list[TaskResult] = Field(default_factory=list)
    failed_tasks: list[TaskResult] = Field(
        default_factory=list, description="Taches ayant echoue"
    )
    aggregates: list[AggregateScores] = Field(default_factory=list)
