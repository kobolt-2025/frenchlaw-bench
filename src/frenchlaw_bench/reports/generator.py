"""Génération de rapports HTML et JSON."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from frenchlaw_bench.config import RESULTS_DIR
from frenchlaw_bench.models.result import BenchmarkRun

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>FrenchLaw Bench — Rapport {{ run.run_id }}</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
  h1 { border-bottom: 2px solid #2563eb; padding-bottom: 0.5rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
  th { background: #f3f4f6; }
  tr:nth-child(even) { background: #f9fafb; }
  .score { font-weight: 600; }
  .good { color: #16a34a; }
  .mid { color: #ca8a04; }
  .bad { color: #dc2626; }
  .meta { color: #6b7280; font-size: 0.875rem; }
</style>
</head>
<body>
<h1>FrenchLaw Bench — Rapport</h1>
<p class="meta">Run ID : {{ run.run_id }} | {{ run.timestamp.strftime('%Y-%m-%d %H:%M') }} | Modèles : {{ run.models | join(', ') }}</p>

<h2>Scores agrégés</h2>
<table>
<tr><th>Modèle</th><th>Answer Score</th><th>Source Score</th><th>Hallucination Rate</th><th>Tâches</th><th>Tokens</th></tr>
{% for agg in run.aggregates %}
<tr>
  <td>{{ agg.model_id }}</td>
  <td class="score {% if agg.answer_score_mean >= 0.7 %}good{% elif agg.answer_score_mean >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f" | format(agg.answer_score_mean * 100) }}%</td>
  <td>{{ "%.1f" | format((agg.source_score_mean or 0) * 100) }}%</td>
  <td>{{ "%.1f" | format((agg.hallucination_rate_mean or 0) * 100) }}%</td>
  <td>{{ agg.total_tasks }}</td>
  <td>{{ "{:,}".format(agg.total_tokens) }}</td>
</tr>
{% endfor %}
</table>

<h2>Scores par catégorie</h2>
{% for agg in run.aggregates %}
<h3>{{ agg.model_id }}</h3>
<table>
<tr><th>Catégorie</th><th>Answer Score</th></tr>
{% for cat, score in agg.answer_score_by_category.items() %}
<tr><td>{{ cat }}</td><td class="score">{{ "%.1f" | format(score * 100) }}%</td></tr>
{% endfor %}
</table>
{% endfor %}

<h2>Détail par tâche</h2>
<table>
<tr><th>#</th><th>Modèle</th><th>Score</th><th>Halluc.</th><th>Latence</th></tr>
{% for r in run.task_results %}
<tr>
  <td>{{ r.task_number }}</td>
  <td>{{ r.model_id }}</td>
  <td class="score {% if r.answer_score >= 0.7 %}good{% elif r.answer_score >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f" | format(r.answer_score * 100) }}%</td>
  <td>{{ "%.1f" | format((r.hallucination_rate or 0) * 100) }}%</td>
  <td>{{ "%.1f" | format(r.latency_seconds) }}s</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""


def generate_report(run: BenchmarkRun, output_dir: Path | None = None) -> Path:
    """Génère un rapport HTML et sauvegarde les résultats JSON."""
    out = output_dir or RESULTS_DIR / run.run_id
    out.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = out / "results.json"
    json_path.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # HTML
    html_path = out / "report.html"
    template = Template(_HTML_TEMPLATE)
    html_path.write_text(template.render(run=run), encoding="utf-8")

    return html_path
