"""Tests pour le rubric parser."""

from frenchlaw_bench.core.rubric_parser import parse_rubric
from frenchlaw_bench.models.enums import Dimension


def test_parse_rubric_basic(sample_rubric_text: str) -> None:
    rubric = parse_rubric(sample_rubric_text)
    assert len(rubric.items) == 10
    assert rubric.total_positive_points == 11.0


def test_parse_rubric_dimensions(sample_rubric_text: str) -> None:
    rubric = parse_rubric(sample_rubric_text)
    assert len(rubric.structure_items) == 2
    assert len(rubric.style_items) == 1
    assert len(rubric.substance_items) == 4
    assert len(rubric.methodologie_items) == 1
    assert len(rubric.negatif_items) == 2


def test_parse_rubric_negative_points(sample_rubric_text: str) -> None:
    rubric = parse_rubric(sample_rubric_text)
    neg = rubric.negatif_items
    assert neg[0].points == -1.0
    assert neg[0].id == "N1"


def test_parse_rubric_half_point() -> None:
    text = """\
[Négatif]
N1 (-0.5pt) : Info hors sujet
"""
    rubric = parse_rubric(text)
    assert rubric.items[0].points == -0.5


def test_parse_rubric_substance_points(sample_rubric_text: str) -> None:
    rubric = parse_rubric(sample_rubric_text)
    sub_items = rubric.substance_items
    points = [i.points for i in sub_items]
    assert points == [2.0, 1.0, 3.0, 1.0]


def test_parse_rubric_empty_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Aucun critère"):
        parse_rubric("")


def test_parse_rubric_unknown_section_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="Section inconnue"):
        parse_rubric("[Inconnu]\nX1 (1pt) : test")


def test_parse_rubric_max_points() -> None:
    text = """\
[Négatif]
N1 (-1pt) (max -5pts) : Hallucination factuelle
"""
    rubric = parse_rubric(text)
    assert rubric.items[0].max_points == -5.0
