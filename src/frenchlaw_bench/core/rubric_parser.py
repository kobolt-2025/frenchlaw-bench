"""Parser de rubrics : texte brut → Rubric structuré.

Format attendu dans le CSV (colonne Rubric) :

    [Structure]
    S1 (1pt) : La réponse est-elle formatée comme une note juridique ?
    S2 (2pts) : La réponse contient-elle des sous-titres pertinents ?

    [Style]
    ST1 (1pt) : Le registre juridique est-il approprié ?

    [Substance]
    SUB1 (2pts) : La réponse mentionne-t-elle l'article 1240 du Code civil ?
    SUB2 (1pt) : La réponse identifie-t-elle la faute ?

    [Méthodologie]
    M1 (1pt) : La réponse suit-elle un raisonnement syllogistique ?

    [Négatif]
    N1 (-1pt) : Hallucination factuelle
    N2 (-0.5pt) : Information hors sujet
    N3 (-2pts) : Citation d'un texte abrogé sans mention
"""

from __future__ import annotations

import re

from frenchlaw_bench.models.enums import Dimension
from frenchlaw_bench.models.task import Rubric, RubricItem

_SECTION_MAP: dict[str, Dimension] = {
    "structure": Dimension.STRUCTURE,
    "style": Dimension.STYLE,
    "substance": Dimension.SUBSTANCE,
    "méthodologie": Dimension.METHODOLOGIE,
    "methodologie": Dimension.METHODOLOGIE,
    "négatif": Dimension.NEGATIF,
    "negatif": Dimension.NEGATIF,
}

_ITEM_RE = re.compile(
    r"^(?P<id>[A-Z]+\d+)\s*\((?P<pts>-?\d+(?:\.\d+)?)\s*pts?\)"
    r"(?:\s*\(max\s*(?P<max>-?\d+(?:\.\d+)?)\s*pts?\))?"
    r"\s*:\s*(?P<desc>.+)$"
)


def parse_rubric(text: str) -> Rubric:
    """Parse un texte de rubric en un objet Rubric structuré."""
    items: list[RubricItem] = []
    current_dimension: Dimension | None = None

    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section_match = re.match(r"^\[(.+)]$", line)
        if section_match:
            section_name = section_match.group(1).strip().lower()
            current_dimension = _SECTION_MAP.get(section_name)
            if current_dimension is None:
                raise ValueError(f"Section inconnue dans le rubric : '{section_match.group(1)}'")
            continue

        item_match = _ITEM_RE.match(line)
        if item_match and current_dimension is not None:
            max_pts = item_match.group("max")
            items.append(
                RubricItem(
                    id=item_match.group("id"),
                    dimension=current_dimension,
                    description=item_match.group("desc").strip(),
                    points=float(item_match.group("pts")),
                    max_points=float(max_pts) if max_pts else None,
                )
            )

    if not items:
        raise ValueError("Aucun critère trouvé dans le rubric")

    return Rubric(items=items)
