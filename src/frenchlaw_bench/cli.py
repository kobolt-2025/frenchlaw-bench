"""CLI pour FrenchLaw Bench."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from frenchlaw_bench.config import RESULTS_DIR
from frenchlaw_bench.core.loader import load_tasks
from frenchlaw_bench.pipeline.runner import run_benchmark
from frenchlaw_bench.reports.generator import generate_report

console = Console()


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "green"
    if score >= 0.4:
        return "yellow"
    return "red"


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val * 100:.1f}%"


def _fmt_usd(val: float) -> str:
    if val < 0.01:
        return f"${val:.4f}"
    return f"${val:.2f}"


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Activer les logs detailles")
def main(verbose: bool) -> None:
    """FrenchLaw Bench — Benchmark LLM pour le droit francais et europeen."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@main.command()
@click.option("--model", "-m", multiple=True, required=True, help="ID du modele OpenRouter")
@click.option("--tasks-csv", type=click.Path(exists=True), default=None, help="Chemin CSV taches")
@click.option("--max-concurrent", "-c", type=int, default=5, help="Concurrence max")
@click.option("--output-dir", "-o", type=click.Path(), default=None, help="Dossier de sortie")
@click.option("--judge-model", "-j", type=str, default=None, help="Modele juge (defaut: JUDGE_MODEL env)")
@click.option("--provider", "-p", type=str, default=None, help="Provider OpenRouter (ex: Cerebras)")
@click.option("--quantization", "-q", type=str, default=None, help="Quantization (ex: fp16, int8)")
def run(
    model: tuple[str, ...],
    tasks_csv: str | None,
    max_concurrent: int,
    output_dir: str | None,
    judge_model: str | None,
    provider: str | None,
    quantization: str | None,
) -> None:
    """Executer le benchmark sur un ou plusieurs modeles."""
    from pathlib import Path

    csv_path = Path(tasks_csv) if tasks_csv else None
    tasks = load_tasks(csv_path)
    console.print(f"[bold]{len(tasks)}[/bold] taches chargees")
    console.print(f"Modeles : {', '.join(model)}")
    if provider:
        console.print(f"Provider : {provider}" + (f" ({quantization})" if quantization else ""))
    if judge_model:
        console.print(f"Juge : {judge_model}")

    benchmark_run = asyncio.run(
        run_benchmark(
            tasks,
            list(model),
            max_concurrent=max_concurrent,
            tasks_csv_path=csv_path,
            judge_model=judge_model,
            provider=provider,
            quantization=quantization,
        )
    )

    out_dir = Path(output_dir) if output_dir else None
    report_path = generate_report(benchmark_run, out_dir)
    console.print(f"\n[green]Rapport genere :[/green] {report_path}")

    # === Resume global ===
    meta = benchmark_run.metadata
    console.print(Panel(
        f"Run ID: [bold]{benchmark_run.run_id}[/bold]\n"
        f"Duree totale: [bold]{meta.duration_seconds:.1f}s[/bold]\n"
        f"Taches: {meta.n_tasks} | Modeles: {', '.join(meta.subject_models)}\n"
        f"Juge: {meta.judge_model}",
        title="FrenchLaw Bench v0.2.0",
    ))

    # === Tableau principal par modele ===
    table = Table(title="Resultats par modele")
    table.add_column("Modele", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("IC 95%", justify="right")
    table.add_column("Source", justify="right")
    table.add_column("Halluc.", justify="right")
    table.add_column("Succes", justify="right")
    table.add_column("Echecs", justify="right")
    table.add_column("Latence P50", justify="right")
    table.add_column("Latence P95", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cout", justify="right")

    for agg in benchmark_run.aggregates:
        score = agg.answer_score_mean
        color = _score_color(score)
        table.add_row(
            agg.model_id,
            f"[{color}]{_fmt_pct(score)}[/{color}]",
            f"[{_fmt_pct(agg.answer_score_ci_lower)} - {_fmt_pct(agg.answer_score_ci_upper)}]",
            _fmt_pct(agg.source_score_mean),
            _fmt_pct(agg.hallucination_rate_mean),
            str(agg.tasks_succeeded),
            str(agg.tasks_failed),
            f"{agg.latency.p50:.1f}s",
            f"{agg.latency.p95:.1f}s",
            f"{agg.total_tokens:,}",
            _fmt_usd(agg.cost_total_usd),
        )

    console.print(table)

    # === Scores par dimension ===
    for agg in benchmark_run.aggregates:
        if agg.answer_score_by_dimension:
            dim_table = Table(title=f"Scores par dimension — {agg.model_id}")
            dim_table.add_column("Dimension", style="bold")
            dim_table.add_column("Score", justify="right")
            for dim in ["Structure", "Style", "Substance", "Methodologie"]:
                val = agg.answer_score_by_dimension.get(dim)
                if val is not None:
                    color = _score_color(val)
                    dim_table.add_row(dim, f"[{color}]{_fmt_pct(val)}[/{color}]")
            console.print(dim_table)

    # === Scores par categorie ===
    for agg in benchmark_run.aggregates:
        cat_table = Table(title=f"Scores par categorie — {agg.model_id}")
        cat_table.add_column("Categorie", style="bold")
        cat_table.add_column("Score", justify="right")
        for cat, score in sorted(agg.answer_score_by_category.items()):
            color = _score_color(score)
            cat_table.add_row(cat, f"[{color}]{_fmt_pct(score)}[/{color}]")
        console.print(cat_table)

    # === Stats hallucinations ===
    for agg in benchmark_run.aggregates:
        if agg.hallucination_total_count > 0:
            h_table = Table(title=f"Hallucinations — {agg.model_id}")
            h_table.add_column("Metrique", style="bold")
            h_table.add_column("Valeur", justify="right")
            h_table.add_row("Total hallucinations", str(agg.hallucination_total_count))
            h_table.add_row("Taches avec hallucinations", str(agg.tasks_with_hallucinations))
            h_table.add_row("Taux moyen", _fmt_pct(agg.hallucination_rate_mean))
            for sev, count in agg.hallucination_severity_counts.items():
                h_table.add_row(f"  {sev}", str(count))
            console.print(h_table)

    # === Stats rubric ===
    for agg in benchmark_run.aggregates:
        r_table = Table(title=f"Criteres rubric — {agg.model_id}")
        r_table.add_column("Metrique", style="bold")
        r_table.add_column("Valeur", justify="right")
        r_table.add_row("Criteres satisfaits", f"{agg.rubric_items_satisfied_total}/{agg.rubric_items_total}")
        r_table.add_row("Taux satisfaction", _fmt_pct(agg.rubric_satisfaction_rate))
        r_table.add_row("Items negatifs declenches", f"{agg.negatif_items_triggered_total}/{agg.negatif_items_total}")
        console.print(r_table)

    # === Detail par tache ===
    detail_table = Table(title="Detail par tache")
    detail_table.add_column("#", justify="right")
    detail_table.add_column("Titre", max_width=40)
    detail_table.add_column("Modele")
    detail_table.add_column("Score", justify="right")
    detail_table.add_column("Halluc.", justify="right")
    detail_table.add_column("Negatif", justify="right")
    detail_table.add_column("Latence", justify="right")
    detail_table.add_column("Cout", justify="right")
    detail_table.add_column("Statut")

    for r in sorted(benchmark_run.task_results, key=lambda x: (x.model_id, x.task_number)):
        if r.error:
            detail_table.add_row(
                str(r.task_number), r.task_title[:40], r.model_id,
                "—", "—", "—",
                f"{r.latency_seconds:.1f}s", "—",
                f"[red]ECHEC[/red]",
            )
        else:
            color = _score_color(r.answer_score)
            detail_table.add_row(
                str(r.task_number),
                r.task_title[:40],
                r.model_id,
                f"[{color}]{_fmt_pct(r.answer_score)}[/{color}]",
                f"{r.hallucination_count}" if r.hallucination_count else "0",
                f"{r.negatif_items_triggered}/{r.negatif_items_total}",
                f"{r.latency_seconds:.1f}s",
                _fmt_usd(r.cost_usd),
                "[green]OK[/green]",
            )

    console.print(detail_table)


@main.command()
@click.argument("run_ids", nargs=-1, required=True)
def compare(run_ids: tuple[str, ...]) -> None:
    """Comparer les resultats de plusieurs runs."""
    table = Table(title="Comparaison de runs")
    table.add_column("Run ID", style="bold")
    table.add_column("Modele")
    table.add_column("Score", justify="right")
    table.add_column("IC 95%", justify="right")
    table.add_column("Halluc.", justify="right")
    table.add_column("Taches", justify="right")
    table.add_column("Cout", justify="right")
    table.add_column("Duree", justify="right")

    for run_id in run_ids:
        results_path = RESULTS_DIR / run_id / "results.json"
        if not results_path.exists():
            console.print(f"[red]Run {run_id} introuvable[/red]")
            continue

        data = json.loads(results_path.read_text())
        duration = data.get("metadata", {}).get("duration_seconds", 0)
        for agg in data.get("aggregates", []):
            table.add_row(
                run_id,
                agg["model_id"],
                f"{agg['answer_score_mean'] * 100:.1f}%",
                f"[{agg.get('answer_score_ci_lower', 0) * 100:.1f}% - {agg.get('answer_score_ci_upper', 0) * 100:.1f}%]",
                f"{agg.get('hallucination_rate_mean', 0) * 100:.1f}%" if agg.get("hallucination_rate_mean") else "—",
                str(agg["total_tasks"]),
                _fmt_usd(agg.get("cost_total_usd", 0)),
                f"{duration:.0f}s",
            )

    console.print(table)


@main.command()
@click.option("--tasks-csv", type=click.Path(exists=True), default=None)
def validate(tasks_csv: str | None) -> None:
    """Valider le fichier de taches (parsing CSV + rubrics)."""
    from pathlib import Path

    try:
        tasks = load_tasks(Path(tasks_csv) if tasks_csv else None)
    except Exception as e:
        console.print(f"[red]Erreur de validation :[/red] {e}")
        raise SystemExit(1) from e

    console.print(f"[green]{len(tasks)} taches validees avec succes[/green]")

    table = Table(title="Resume des taches")
    table.add_column("#", justify="right")
    table.add_column("Categorie")
    table.add_column("Sous-cat.")
    table.add_column("Type")
    table.add_column("Titre", max_width=45)
    table.add_column("Pts+", justify="right")
    table.add_column("Pts-", justify="right")
    table.add_column("Items", justify="right")
    table.add_column("Docs", justify="right")

    for t in tasks:
        neg_pts = sum(abs(i.points) for i in t.rubric.items if i.points < 0)
        table.add_row(
            str(t.number),
            t.category.value,
            t.sub_category.value[:20],
            t.task_type.value[:20],
            t.title[:45],
            f"{t.rubric.total_positive_points:.0f}",
            f"-{neg_pts:.1f}" if neg_pts else "0",
            str(len(t.rubric.items)),
            str(len(t.documents)),
        )

    console.print(table)
