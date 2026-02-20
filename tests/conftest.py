"""Fixtures partagées pour les tests."""

from __future__ import annotations

import pytest

from frenchlaw_bench.models.enums import Category, Dimension, SubCategory, TaskType
from frenchlaw_bench.models.task import Rubric, RubricItem, Task


@pytest.fixture
def sample_rubric_text() -> str:
    return """\
[Structure]
S1 (1pt) : La réponse est structurée sous forme de note professionnelle
S2 (1pt) : Les parties sont numérotées

[Style]
ST1 (1pt) : Ton professionnel d'avocat conseil

[Substance]
SUB1 (2pts) : Mentionne l'article 1240 du Code civil
SUB2 (1pt) : Identifie la faute comme condition de la responsabilité
SUB3 (3pts) : Analyse le lien de causalité
SUB4 (1pt) : Mentionne le préjudice réparable

[Méthodologie]
M1 (1pt) : Suit un raisonnement syllogistique (majeure/mineure/conclusion)

[Négatif]
N1 (-1pt) : Hallucination factuelle
N2 (-0.5pt) : Information exacte mais hors sujet
"""


@pytest.fixture
def sample_rubric() -> Rubric:
    return Rubric(
        items=[
            RubricItem(id="S1", dimension=Dimension.STRUCTURE, description="Note pro", points=1),
            RubricItem(id="ST1", dimension=Dimension.STYLE, description="Ton pro", points=1),
            RubricItem(id="SUB1", dimension=Dimension.SUBSTANCE, description="Art. 1240", points=2),
            RubricItem(id="SUB2", dimension=Dimension.SUBSTANCE, description="Faute", points=1),
            RubricItem(id="SUB3", dimension=Dimension.SUBSTANCE, description="Causalité", points=3),
            RubricItem(id="M1", dimension=Dimension.METHODOLOGIE, description="Syllogisme", points=1),
            RubricItem(id="N1", dimension=Dimension.NEGATIF, description="Hallucination", points=-1),
        ]
    )


@pytest.fixture
def sample_task(sample_rubric: Rubric) -> Task:
    return Task(
        number=99,
        category=Category.DROIT_PRIVE,
        sub_category=SubCategory.CONTRATS,
        task_type=TaskType.RECHERCHE_JURIDIQUE,
        title="Test responsabilité délictuelle",
        prompt="Analysez les conditions de la responsabilité délictuelle.",
        documents=[],
        rubric=sample_rubric,
    )
