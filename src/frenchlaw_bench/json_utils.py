"""Parsing JSON robuste pour les reponses LLM."""

from __future__ import annotations

import json
import re

# Regex pour retirer les trailing commas avant } ou ]
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

# Regex pour extraire JSON d'un bloc markdown ```json ... ```
_MARKDOWN_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def parse_llm_json(text: str) -> dict | list:
    """Parse du JSON issu d'un LLM avec tolerances pour les erreurs courantes.

    Gere :
    - JSON valide direct
    - JSON enveloppe dans un bloc markdown ```json ... ```
    - Trailing commas (,} ou ,])
    - Texte avant/apres le JSON (extraction du premier objet/array)
    """
    # 1. Essai direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = text.strip()

    # 2. Extraction depuis un bloc markdown
    md_match = _MARKDOWN_BLOCK_RE.search(cleaned)
    if md_match:
        extracted = md_match.group(1).strip()
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            # Essayer avec nettoyage trailing commas
            fixed = _TRAILING_COMMA_RE.sub(r"\1", extracted)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # 3. Extraction du bloc JSON (premier { ... dernier } ou [ ... ])
    obj_start = cleaned.find("{")
    arr_start = cleaned.find("[")

    if obj_start >= 0 and (arr_start < 0 or obj_start <= arr_start):
        end = cleaned.rfind("}") + 1
        if end > obj_start:
            block = cleaned[obj_start:end]
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                fixed = _TRAILING_COMMA_RE.sub(r"\1", block)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
    elif arr_start >= 0:
        end = cleaned.rfind("]") + 1
        if end > arr_start:
            block = cleaned[arr_start:end]
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                fixed = _TRAILING_COMMA_RE.sub(r"\1", block)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

    # 4. Dernier recours : trailing commas sur le texte entier
    fixed = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    return json.loads(fixed)
