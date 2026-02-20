"""Detecteur d'hallucinations en 2 etapes avec classification de severite."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from frenchlaw_bench.json_utils import parse_llm_json
from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.models.result import HallucinationDetail
from frenchlaw_bench.scoring.prompts import (
    HALLUCINATION_EXTRACT_PROMPT,
    HALLUCINATION_EXTRACT_SYSTEM,
    HALLUCINATION_VERIFY_PROMPT,
    HALLUCINATION_VERIFY_SYSTEM,
)

logger = logging.getLogger(__name__)

# Penalites par severite (inspirees de HalluDetect, EMNLP 2025)
SEVERITY_PENALTIES: dict[str, float] = {
    "critical": 2.0,  # Article invente, jurisprudence fictive
    "major": 1.0,     # Mauvaise juridiction, date incorrecte
    "minor": 0.3,     # Imprecision legere
}


@dataclass
class HallucinationResult:
    total_claims: int
    hallucinated_claims: int
    rate: float
    penalty_points: float
    severity_counts: dict[str, int] = field(default_factory=dict)
    details: list[HallucinationDetail] = field(default_factory=list)


async def _verify_single_claim(
    client: BaseLLMClient,
    claim_text: str,
    category: str,
    task_title: str,
    source_context: str,
) -> HallucinationDetail | None:
    """Verifie un seul claim."""
    verify_prompt = HALLUCINATION_VERIFY_PROMPT.format(
        claim=claim_text,
        category=category,
        task_title=task_title,
        source_context=source_context,
    )
    verify_resp = await client.complete(
        verify_prompt, system=HALLUCINATION_VERIFY_SYSTEM, temperature=0.0
    )

    try:
        verify_data = parse_llm_json(verify_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de verifier le claim: %s", claim_text[:50])
        return None

    return HallucinationDetail(
        claim=claim_text,
        hallucinated=verify_data.get("hallucinated", False),
        severity=verify_data.get("severity") or "minor",
        category=verify_data.get("category") or category,
        reasoning=verify_data.get("reasoning") or "",
    )


async def detect_hallucinations(
    client: BaseLLMClient,
    response: str,
    task_title: str,
    source_context: str = "Pas de documents source (tache knowledge-only)",
    max_penalty: float | None = None,
) -> HallucinationResult:
    """Pipeline de detection d'hallucinations en 2 etapes.

    1. Extraction des claims factuels (avec categories)
    2. Verification parallele de chaque claim avec classification de severite

    Args:
        max_penalty: Plafond de penalite (si None, pas de plafond).
    """
    # Etape 1 : extraction
    extract_prompt = HALLUCINATION_EXTRACT_PROMPT.format(response=response)
    extract_resp = await client.complete(
        extract_prompt, system=HALLUCINATION_EXTRACT_SYSTEM, temperature=0.0
    )

    try:
        extract_data = parse_llm_json(extract_resp.content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Impossible de parser les claims extraits")
        return HallucinationResult(0, 0, 0.0, 0.0)

    claims = extract_data.get("claims", [])
    if not claims:
        return HallucinationResult(0, 0, 0.0, 0.0)

    # Etape 2 : verification en parallele
    coros = [
        _verify_single_claim(
            client,
            claim_data.get("claim", ""),
            claim_data.get("category", "other_fact"),
            task_title,
            source_context,
        )
        for claim_data in claims
        if claim_data.get("claim", "").strip()
    ]

    results = await asyncio.gather(*coros, return_exceptions=True)

    details: list[HallucinationDetail] = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Erreur verification claim: %s", r)
        elif r is not None:
            details.append(r)

    # Calcul des metriques
    hallucinated_details = [d for d in details if d.hallucinated]
    hallucinated_count = len(hallucinated_details)
    total = len(details)
    rate = hallucinated_count / total if total > 0 else 0.0

    # Penalite ponderee par severite
    severity_counts: dict[str, int] = {"critical": 0, "major": 0, "minor": 0}
    penalty = 0.0
    for d in hallucinated_details:
        sev = d.severity if d.severity in SEVERITY_PENALTIES else "minor"
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        penalty += SEVERITY_PENALTIES[sev]

    # Plafonner la penalite si demande
    if max_penalty is not None and penalty > max_penalty:
        penalty = max_penalty

    return HallucinationResult(
        total_claims=total,
        hallucinated_claims=hallucinated_count,
        rate=rate,
        penalty_points=penalty,
        severity_counts=severity_counts,
        details=details,
    )
