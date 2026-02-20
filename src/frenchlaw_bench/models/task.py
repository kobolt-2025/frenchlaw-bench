"""Modèles pour les tâches et rubrics du benchmark."""

from __future__ import annotations

from pydantic import BaseModel, Field

from frenchlaw_bench.models.enums import Category, Dimension, SubCategory, TaskType


class RubricItem(BaseModel):
    """Un critère individuel dans un rubric."""

    id: str = Field(description="Identifiant unique du critère (ex: S1, SUB3, N2)")
    dimension: Dimension
    description: str = Field(description="Question oui/non évaluable")
    points: float = Field(description="Points attribués (négatif pour pénalités)")
    max_points: float | None = Field(
        default=None,
        description="Pour les pénalités cumulatives, le max de points retirables",
    )


class Rubric(BaseModel):
    """Grille de notation complète pour une tâche."""

    items: list[RubricItem]

    @property
    def total_positive_points(self) -> float:
        return sum(item.points for item in self.items if item.points > 0)

    @property
    def structure_items(self) -> list[RubricItem]:
        return [i for i in self.items if i.dimension == Dimension.STRUCTURE]

    @property
    def style_items(self) -> list[RubricItem]:
        return [i for i in self.items if i.dimension == Dimension.STYLE]

    @property
    def substance_items(self) -> list[RubricItem]:
        return [i for i in self.items if i.dimension == Dimension.SUBSTANCE]

    @property
    def methodologie_items(self) -> list[RubricItem]:
        return [i for i in self.items if i.dimension == Dimension.METHODOLOGIE]

    @property
    def negatif_items(self) -> list[RubricItem]:
        return [i for i in self.items if i.dimension == Dimension.NEGATIF]


class Task(BaseModel):
    """Une tâche du benchmark FrenchLaw Bench."""

    number: int = Field(description="Identifiant numérique de la tâche")
    category: Category
    sub_category: SubCategory
    task_type: TaskType
    title: str = Field(description="Description brève de la tâche")
    prompt: str = Field(description="Prompt exact donné au LLM")
    documents: list[str] = Field(
        default_factory=list,
        description="Noms des PDFs fournis en contexte (vide si knowledge-only)",
    )
    rubric: Rubric
    rubric_raw: str = Field(default="", description="Texte brut du rubric original")
