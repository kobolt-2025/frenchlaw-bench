"""Extraction de texte depuis des documents PDF."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from frenchlaw_bench.config import DATA_DIR


def extract_pdf_text(pdf_path: Path) -> str:
    """Extrait le texte d'un PDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def load_task_documents(document_names: list[str], subdir: str = "core") -> str:
    """Charge et concatène les textes des documents d'une tâche."""
    if not document_names:
        return ""

    docs_dir = DATA_DIR / subdir / "documents"
    texts = []

    for name in document_names:
        pdf_path = docs_dir / name
        if pdf_path.exists():
            text = extract_pdf_text(pdf_path)
            texts.append(f"--- Document : {name} ---\n{text}")
        else:
            texts.append(f"--- Document : {name} --- [FICHIER MANQUANT]")

    return "\n\n".join(texts)
