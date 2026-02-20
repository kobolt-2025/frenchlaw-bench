"""Chargement des données de ground truth pour le workflow Cession d'Actions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from frenchlaw_bench.config import DATA_DIR
from frenchlaw_bench.models.workflow import CessionActions


def load_ground_truth(
    csv_path: Path | None = None,
) -> list[tuple[str, CessionActions]]:
    """Charge les ground truth depuis le CSV.

    Retourne une liste de tuples (nom_document, ground_truth).

    Colonnes attendues : Document, GroundTruth (JSON)
    """
    if csv_path is None:
        csv_path = DATA_DIR / "workflows" / "cession_actions" / "ground_truth.csv"

    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_name = row["Document"]
            gt_data = json.loads(row["GroundTruth"])
            gt = CessionActions.model_validate(gt_data)
            results.append((doc_name, gt))

    return results
