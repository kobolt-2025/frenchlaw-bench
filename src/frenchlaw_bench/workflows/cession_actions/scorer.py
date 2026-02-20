"""Scoring pour le workflow Cession d'Actions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from frenchlaw_bench.llm.base import BaseLLMClient
from frenchlaw_bench.models.workflow import CessionActions

logger = logging.getLogger(__name__)

_TEXT_FIELDS = {
    "modalites_paiement",
    "criteres",
    "duree",
    "type_franchise",
    "perimetre_geographique",
    "activite",
    "contrepartie",
    "droit_applicable",
    "juridiction_competente",
    "frais_droits_enregistrement",
    "repartition_frais",
    "forme_juridique",
    "rcs",
    "siege_social",
    "categorie",
    "date_signature",
}

_TEXT_JUDGE_PROMPT = """\
Compare ces deux valeurs pour un champ de cession d'actions :

Champ : {field}
Valeur attendue : {expected}
Valeur extraite : {extracted}

Les valeurs sont-elles sémantiquement équivalentes (même information, \
même sens, éventuellement formulées différemment) ?

Réponds UNIQUEMENT : {{"match": true/false, "reasoning": "..."}}
"""


@dataclass
class WorkflowScore:
    total_fields: int
    exact_matches: int
    llm_matches: int
    accuracy: float
    details: list[dict]


def _flatten(obj: dict, prefix: str = "") -> dict[str, object]:
    """Aplatit un dict imbriqué en clés dotées."""
    flat: dict[str, object] = {}
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        elif isinstance(value, list):
            flat[full_key] = value
        else:
            flat[full_key] = value
    return flat


async def score_extraction(
    extracted: CessionActions,
    ground_truth: CessionActions,
    judge_client: BaseLLMClient,
) -> WorkflowScore:
    """Score une extraction par rapport au ground truth."""
    gt_flat = _flatten(ground_truth.model_dump())
    ex_flat = _flatten(extracted.model_dump())

    details = []
    exact_matches = 0
    llm_matches = 0
    total = 0

    for key, gt_val in gt_flat.items():
        if gt_val is None or gt_val == "" or gt_val == []:
            continue

        total += 1
        ex_val = ex_flat.get(key)
        field_name = key.split(".")[-1]

        if ex_val == gt_val:
            exact_matches += 1
            details.append({"field": key, "match": "exact", "expected": gt_val, "got": ex_val})
            continue

        # Pour les champs textuels, utiliser LLM-as-judge
        if field_name in _TEXT_FIELDS and ex_val:
            prompt = _TEXT_JUDGE_PROMPT.format(
                field=key, expected=gt_val, extracted=ex_val
            )
            resp = await judge_client.complete(prompt, temperature=0.0)
            try:
                data = json.loads(resp.content)
                if isinstance(data, str):
                    data = json.loads(data)
            except json.JSONDecodeError:
                text = resp.content
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(text[start:end])
                else:
                    data = {"match": False}

            if data.get("match"):
                llm_matches += 1
                details.append({"field": key, "match": "llm", "expected": gt_val, "got": ex_val})
                continue

        details.append({"field": key, "match": "miss", "expected": gt_val, "got": ex_val})

    matched = exact_matches + llm_matches
    accuracy = matched / total if total > 0 else 0.0

    return WorkflowScore(
        total_fields=total,
        exact_matches=exact_matches,
        llm_matches=llm_matches,
        accuracy=accuracy,
        details=details,
    )
