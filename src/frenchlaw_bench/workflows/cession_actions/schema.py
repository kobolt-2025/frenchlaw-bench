"""Schema JSON pour le workflow Cession d'Actions."""

from __future__ import annotations

import json

from frenchlaw_bench.models.workflow import CessionActions

CESSION_ACTIONS_SCHEMA = CessionActions.model_json_schema()


def get_schema_json() -> str:
    """Retourne le schema JSON formaté."""
    return json.dumps(CESSION_ACTIONS_SCHEMA, indent=2, ensure_ascii=False)


EXTRACTION_PROMPT = """\
Tu es un avocat spécialisé en droit des sociétés français. Analyse le document \
de cession d'actions suivant et extrais les informations structurées selon le \
schema JSON fourni.

## Schema JSON attendu
{schema}

## Document
{document}

## Instructions
- Extrais chaque champ du schema à partir du document.
- Si une information n'est pas présente dans le document, laisse le champ vide ou null.
- Pour les montants, utilise des nombres (pas de formatage texte).
- Pour les dates, utilise le format YYYY-MM-DD.
- Réponds UNIQUEMENT avec le JSON structuré, sans commentaire.
"""
