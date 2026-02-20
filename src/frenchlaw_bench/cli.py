"""CLI pour FrenchLaw Bench."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.table import Table

from frenchlaw_bench.config import RESULTS_DIR
from frenchlaw_bench.core.loader import load_tasks
from frenchlaw_bench.pipeline.runner import run_benchmark
from frenchlaw_bench.reports.generator import generate_report

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Activer les logs détaillés")
def main(verbose: bool) -> None:
    """FrenchLaw Bench — Benchmark LLM pour le droit français et européen."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@main.command()
@click.option("--model", "-m", multiple=True, required=True, help="ID du modèle OpenRouter")
@click.option("--tasks-csv", type=click.Path(exists=True), default=None, help="Chemin CSV tâches")
@click.option("--max-concurrent", "-c", type=int, default=5, help="Concurrence max")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="Dossier de sortie")
def run(
    model: tuple[str, ...],
    tasks_csv: str | None,
    max_concurrent: int,
    output_dir: str | None,
) -> None:
    """Exécuter le benchmark sur un ou plusieurs modèles."""
    from pathlib import Path

    tasks = load_tasks(Path(tasks_csv) if tasks_csv else None)
    console.print(f"[bold]{len(tasks)}[/bold] tâches chargées")
    console.print(f"Modèles : {', '.join(model)}")

    benchmark_run = asyncio.run(
        run_benchmark(tasks, list(model), max_concurrent=max_concurrent)
    )

    out_dir = Path(output_dir) if output_dir else None
    report_path = generate_report(benchmark_run, out_dir)
    console.print(f"\n[green]Rapport généré :[/green] {report_path}")

    # Affichage résumé
    table = Table(title="Résultats FrenchLaw Bench")
    table.add_column("Modèle", style="bold")
    table.add_column("Answer Score", justify="right")
    table.add_column("Source Score", justify="right")
    table.add_column("Halluc. Rate", justify="right")

    for agg in benchmark_run.aggregates:
        answer = f"{agg.answer_score_mean * 100:.1f}%"
        source = f"{(agg.source_score_mean or 0) * 100:.1f}%"
        halluc = f"{(agg.hallucination_rate_mean or 0) * 100:.1f}%"
        table.add_row(agg.model_id, answer, source, halluc)

    console.print(table)


@main.command()
@click.argument("run_ids", nargs=-1, required=True)
def compare(run_ids: tuple[str, ...]) -> None:
    """Comparer les résultats de plusieurs runs."""
    table = Table(title="Comparaison de runs")
    table.add_column("Run ID", style="bold")
    table.add_column("Modèle")
    table.add_column("Answer Score", justify="right")
    table.add_column("Tâches", justify="right")

    for run_id in run_ids:
        results_path = RESULTS_DIR / run_id / "results.json"
        if not results_path.exists():
            console.print(f"[red]Run {run_id} introuvable[/red]")
            continue

        data = json.loads(results_path.read_text())
        for agg in data.get("aggregates", []):
            table.add_row(
                run_id,
                agg["model_id"],
                f"{agg['answer_score_mean'] * 100:.1f}%",
                str(agg["total_tasks"]),
            )

    console.print(table)


@main.command()
@click.option("--tasks-csv", type=click.Path(exists=True), default=None)
def validate(tasks_csv: str | None) -> None:
    """Valider le fichier de tâches (parsing CSV + rubrics)."""
    from pathlib import Path

    try:
        tasks = load_tasks(Path(tasks_csv) if tasks_csv else None)
    except Exception as e:
        console.print(f"[red]Erreur de validation :[/red] {e}")
        raise SystemExit(1) from e

    console.print(f"[green]{len(tasks)} tâches validées avec succès[/green]")

    table = Table(title="Résumé des tâches")
    table.add_column("#", justify="right")
    table.add_column("Catégorie")
    table.add_column("Type")
    table.add_column("Titre")
    table.add_column("Pts+", justify="right")
    table.add_column("Items", justify="right")
    table.add_column("Docs", justify="right")

    for t in tasks:
        table.add_row(
            str(t.number),
            t.category.value,
            t.task_type.value,
            t.title[:50],
            f"{t.rubric.total_positive_points:.0f}",
            str(len(t.rubric.items)),
            str(len(t.documents)),
        )

    console.print(table)
