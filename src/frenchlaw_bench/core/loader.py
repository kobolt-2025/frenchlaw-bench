"""Chargement des tâches depuis le fichier CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from frenchlaw_bench.config import DATA_DIR
from frenchlaw_bench.core.rubric_parser import parse_rubric
from frenchlaw_bench.models.enums import Category, SubCategory, TaskType
from frenchlaw_bench.models.task import Task


def load_tasks(csv_path: Path | None = None) -> list[Task]:
    """Charge toutes les tâches depuis le fichier CSV.

    Colonnes attendues :
        Number, Category, SubCategory, TaskType, Title, Prompt, Documents, Rubric
    """
    if csv_path is None:
        csv_path = DATA_DIR / "core" / "tasks.csv"

    tasks: list[Task] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs_raw = row.get("Documents", "").strip()
            documents = (
                [d.strip() for d in docs_raw.split(";") if d.strip()]
                if docs_raw and docs_raw.upper() != "N/A"
                else []
            )

            rubric_raw = row["Rubric"]
            rubric = parse_rubric(rubric_raw)

            task = Task(
                number=int(row["Number"]),
                category=Category(row["Category"]),
                sub_category=SubCategory(row["SubCategory"]),
                task_type=TaskType(row["TaskType"]),
                title=row["Title"],
                prompt=row["Prompt"],
                documents=documents,
                rubric=rubric,
                rubric_raw=rubric_raw,
            )
            tasks.append(task)

    return tasks
