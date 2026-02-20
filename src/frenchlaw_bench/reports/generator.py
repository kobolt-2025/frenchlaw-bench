"""Generation de rapports HTML et JSON."""

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
  :root { --blue: #2563eb; --green: #16a34a; --yellow: #ca8a04; --red: #dc2626; --gray: #6b7280; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fafafa; }
  h1 { border-bottom: 3px solid var(--blue); padding-bottom: 0.5rem; }
  h2 { color: var(--blue); margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }
  h3 { color: #374151; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
  th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
  th { background: #f3f4f6; font-weight: 600; }
  tr:nth-child(even) { background: #f9fafb; }
  .score { font-weight: 700; font-variant-numeric: tabular-nums; }
  .good { color: var(--green); }
  .mid { color: var(--yellow); }
  .bad { color: var(--red); }
  .meta { color: var(--gray); font-size: 0.85rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1rem 0; }
  .card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; }
  .card h4 { margin: 0 0 0.5rem 0; font-size: 0.85rem; color: var(--gray); text-transform: uppercase; letter-spacing: 0.5px; }
  .card .value { font-size: 1.8rem; font-weight: 700; }
  .card .sub { font-size: 0.8rem; color: var(--gray); margin-top: 0.2rem; }
  .bar { height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin-top: 4px; }
  .bar-fill { height: 100%; border-radius: 4px; }
  .bar-fill.good { background: var(--green); }
  .bar-fill.mid { background: var(--yellow); }
  .bar-fill.bad { background: var(--red); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
  .badge-ok { background: #dcfce7; color: var(--green); }
  .badge-fail { background: #fee2e2; color: var(--red); }
  .badge-warn { background: #fef3c7; color: var(--yellow); }
  details { margin: 0.5rem 0; }
  summary { cursor: pointer; font-weight: 600; padding: 0.3rem 0; }
  .halluc-detail { background: #fef2f2; border-left: 3px solid var(--red); padding: 0.5rem; margin: 0.3rem 0; font-size: 0.85rem; }
  .evidence { background: #f0fdf4; border-left: 3px solid var(--green); padding: 0.5rem; margin: 0.3rem 0; font-size: 0.85rem; }
  .section-sep { border-top: 2px solid #e5e7eb; margin-top: 3rem; padding-top: 1rem; }
  @media print { body { max-width: 100%; } .card { break-inside: avoid; } }
</style>
</head>
<body>

<h1>FrenchLaw Bench — Rapport</h1>
<p class="meta">
  Run ID : {{ run.run_id }} |
  {{ run.timestamp.strftime('%Y-%m-%d %H:%M') }} |
  Duree : {{ "%.0f"|format(run.metadata.duration_seconds) }}s |
  Juge : {{ run.metadata.judge_model }}
</p>
<p class="meta">
  Modeles : {{ run.models | join(', ') }} |
  Taches : {{ run.metadata.n_tasks }} |
  Dataset SHA256 : {{ run.metadata.dataset_sha256[:16] }}...
</p>

<!-- ===== CARTES RESUME ===== -->
{% for agg in run.aggregates %}
<h2>{{ agg.model_id }}</h2>

<div class="grid">
  <div class="card">
    <h4>Score Global</h4>
    <div class="value {% if agg.answer_score_mean >= 0.7 %}good{% elif agg.answer_score_mean >= 0.4 %}mid{% else %}bad{% endif %}">
      {{ "%.1f"|format(agg.answer_score_mean * 100) }}%
    </div>
    <div class="sub">IC 95% : [{{ "%.1f"|format(agg.answer_score_ci_lower * 100) }}% — {{ "%.1f"|format(agg.answer_score_ci_upper * 100) }}%]</div>
    <div class="sub">Median : {{ "%.1f"|format(agg.answer_score_median * 100) }}% | Ecart-type : {{ "%.1f"|format(agg.answer_score_std * 100) }}%</div>
  </div>

  <div class="card">
    <h4>Taches</h4>
    <div class="value">{{ agg.tasks_succeeded }}/{{ agg.total_tasks }}</div>
    <div class="sub">
      <span class="badge badge-ok">{{ agg.tasks_succeeded }} reussies</span>
      {% if agg.tasks_failed > 0 %}<span class="badge badge-fail">{{ agg.tasks_failed }} echecs</span>{% endif %}
    </div>
  </div>

  <div class="card">
    <h4>Hallucinations</h4>
    <div class="value {% if agg.hallucination_total_count == 0 %}good{% elif agg.hallucination_total_count <= 5 %}mid{% else %}bad{% endif %}">
      {{ agg.hallucination_total_count }}
    </div>
    <div class="sub">
      {{ agg.tasks_with_hallucinations }} taches affectees |
      Taux moyen : {{ "%.1f"|format((agg.hallucination_rate_mean or 0) * 100) }}%
    </div>
    <div class="sub">
      Critical: {{ agg.hallucination_severity_counts.get('critical', 0) }} |
      Major: {{ agg.hallucination_severity_counts.get('major', 0) }} |
      Minor: {{ agg.hallucination_severity_counts.get('minor', 0) }}
    </div>
  </div>

  <div class="card">
    <h4>Source Score</h4>
    <div class="value {% if (agg.source_score_mean or 0) >= 0.7 %}good{% elif (agg.source_score_mean or 0) >= 0.4 %}mid{% else %}bad{% endif %}">
      {{ "%.1f"|format((agg.source_score_mean or 0) * 100) }}%
    </div>
    <div class="sub">Attribution des sources juridiques</div>
  </div>

  <div class="card">
    <h4>Criteres Rubric</h4>
    <div class="value">{{ agg.rubric_items_satisfied_total }}/{{ agg.rubric_items_total }}</div>
    <div class="sub">Taux satisfaction : {{ "%.1f"|format(agg.rubric_satisfaction_rate * 100) }}%</div>
    <div class="sub">Negatifs declenches : {{ agg.negatif_items_triggered_total }}/{{ agg.negatif_items_total }}</div>
  </div>

  <div class="card">
    <h4>Latence</h4>
    <div class="value">{{ "%.1f"|format(agg.latency.p50) }}s</div>
    <div class="sub">P50 | P95 : {{ "%.1f"|format(agg.latency.p95) }}s | P99 : {{ "%.1f"|format(agg.latency.p99) }}s</div>
    <div class="sub">Min : {{ "%.1f"|format(agg.latency.min) }}s | Max : {{ "%.1f"|format(agg.latency.max) }}s</div>
  </div>

  <div class="card">
    <h4>Tokens</h4>
    <div class="value">{{ "{:,}".format(agg.tokens.total) }}</div>
    <div class="sub">Input : {{ "{:,}".format(agg.tokens.total_input) }} | Output : {{ "{:,}".format(agg.tokens.total_output) }}</div>
    <div class="sub">Moy/tache : {{ "{:,.0f}".format(agg.tokens.mean_total_per_task) }}</div>
  </div>

  <div class="card">
    <h4>Cout Estime</h4>
    <div class="value">${{ "%.2f"|format(agg.cost_total_usd) }}</div>
    <div class="sub">${{ "%.4f"|format(agg.cost_per_task_usd) }} par tache</div>
  </div>
</div>

<!-- Scores par dimension -->
<h3>Scores par dimension</h3>
<table>
<tr><th>Dimension</th><th>Score</th><th style="width:40%">Barre</th></tr>
{% for dim in ['Structure', 'Style', 'Substance', 'Methodologie'] %}
{% set val = agg.answer_score_by_dimension.get(dim, 0) %}
<tr>
  <td><strong>{{ dim }}</strong></td>
  <td class="score {% if val >= 0.7 %}good{% elif val >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f"|format(val * 100) }}%</td>
  <td>
    <div class="bar"><div class="bar-fill {% if val >= 0.7 %}good{% elif val >= 0.4 %}mid{% else %}bad{% endif %}" style="width: {{ "%.0f"|format(val * 100) }}%"></div></div>
  </td>
</tr>
{% endfor %}
</table>

<!-- Scores par categorie -->
<h3>Scores par categorie</h3>
<table>
<tr><th>Categorie</th><th>Score</th><th style="width:40%">Barre</th></tr>
{% for cat, score in agg.answer_score_by_category.items() | sort %}
<tr>
  <td>{{ cat }}</td>
  <td class="score {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f"|format(score * 100) }}%</td>
  <td>
    <div class="bar"><div class="bar-fill {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}" style="width: {{ "%.0f"|format(score * 100) }}%"></div></div>
  </td>
</tr>
{% endfor %}
</table>

<!-- Scores par sous-categorie -->
{% if agg.answer_score_by_sub_category %}
<h3>Scores par sous-categorie</h3>
<table>
<tr><th>Sous-categorie</th><th>Score</th><th style="width:40%">Barre</th></tr>
{% for cat, score in agg.answer_score_by_sub_category.items() | sort %}
<tr>
  <td>{{ cat }}</td>
  <td class="score {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f"|format(score * 100) }}%</td>
  <td>
    <div class="bar"><div class="bar-fill {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}" style="width: {{ "%.0f"|format(score * 100) }}%"></div></div>
  </td>
</tr>
{% endfor %}
</table>
{% endif %}

<!-- Scores par type de tache -->
{% if agg.answer_score_by_task_type %}
<h3>Scores par type de tache</h3>
<table>
<tr><th>Type</th><th>Score</th><th style="width:40%">Barre</th></tr>
{% for tt, score in agg.answer_score_by_task_type.items() | sort %}
<tr>
  <td>{{ tt }}</td>
  <td class="score {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f"|format(score * 100) }}%</td>
  <td>
    <div class="bar"><div class="bar-fill {% if score >= 0.7 %}good{% elif score >= 0.4 %}mid{% else %}bad{% endif %}" style="width: {{ "%.0f"|format(score * 100) }}%"></div></div>
  </td>
</tr>
{% endfor %}
</table>
{% endif %}

{% endfor %}

<!-- ===== DETAIL PAR TACHE ===== -->
<div class="section-sep"></div>
<h2>Detail par tache</h2>
<table>
<tr>
  <th>#</th><th>Titre</th><th>Modele</th><th>Score</th>
  <th>Structure</th><th>Style</th><th>Substance</th><th>Methodo</th>
  <th>Halluc.</th><th>Negatif</th><th>Source</th><th>Latence</th><th>Cout</th><th>Statut</th>
</tr>
{% for r in run.task_results | sort(attribute='task_number') %}
<tr>
  <td>{{ r.task_number }}</td>
  <td>{{ r.task_title[:40] }}</td>
  <td>{{ r.model_id }}</td>
  {% if r.error %}
  <td colspan="10" style="color: var(--red)">ECHEC : {{ r.error[:60] }}</td>
  <td><span class="badge badge-fail">ECHEC</span></td>
  {% else %}
  <td class="score {% if r.answer_score >= 0.7 %}good{% elif r.answer_score >= 0.4 %}mid{% else %}bad{% endif %}">{{ "%.1f"|format(r.answer_score * 100) }}%</td>
  <td class="score">{{ "%.0f"|format((r.answer_score_by_dimension.get('Structure', 0)) * 100) }}%</td>
  <td class="score">{{ "%.0f"|format((r.answer_score_by_dimension.get('Style', 0)) * 100) }}%</td>
  <td class="score">{{ "%.0f"|format((r.answer_score_by_dimension.get('Substance', 0)) * 100) }}%</td>
  <td class="score">{{ "%.0f"|format((r.answer_score_by_dimension.get('Methodologie', 0)) * 100) }}%</td>
  <td>{{ r.hallucination_count }}</td>
  <td>{{ r.negatif_items_triggered }}/{{ r.negatif_items_total }}</td>
  <td>{{ "%.0f"|format((r.source_score or 0) * 100) }}%</td>
  <td>{{ "%.1f"|format(r.latency_seconds) }}s</td>
  <td>${{ "%.3f"|format(r.cost_usd) }}</td>
  <td><span class="badge badge-ok">OK</span></td>
  {% endif %}
</tr>
{% endfor %}
</table>

<!-- ===== DETAIL RUBRIC PAR TACHE ===== -->
<div class="section-sep"></div>
<h2>Detail des criteres par tache</h2>
{% for r in run.task_results | sort(attribute='task_number') %}
{% if not r.error %}
<details>
  <summary>Tache {{ r.task_number }} — {{ r.task_title }} ({{ r.model_id }}) — {{ "%.1f"|format(r.answer_score * 100) }}%</summary>

  <table>
  <tr><th>ID</th><th>Dimension</th><th>Resultat</th><th>Confiance</th><th>Raisonnement</th></tr>
  {% for item in r.rubric_results %}
  <tr>
    <td>{{ item.item_id }}</td>
    <td>{{ item.dimension }}</td>
    <td>{% if item.satisfied %}<span class="badge badge-ok">Satisfait</span>{% else %}<span class="badge badge-fail">Non satisfait</span>{% endif %}</td>
    <td>{{ "%.0f"|format(item.confidence * 100) }}%</td>
    <td>{{ item.reasoning[:120] }}</td>
  </tr>
  {% endfor %}
  {% for item in r.negatif_results %}
  <tr style="background: {% if item.satisfied %}#fef2f2{% else %}#f0fdf4{% endif %}">
    <td>{{ item.item_id }}</td>
    <td>Negatif</td>
    <td>{% if item.satisfied %}<span class="badge badge-fail">Declenche</span>{% else %}<span class="badge badge-ok">Non declenche</span>{% endif %}</td>
    <td>{{ "%.0f"|format(item.confidence * 100) }}%</td>
    <td>{{ item.reasoning[:120] }}</td>
  </tr>
  {% endfor %}
  </table>

  {% if r.hallucination_details %}
  <h4>Hallucinations detectees</h4>
  {% for h in r.hallucination_details %}
  {% if h.hallucinated %}
  <div class="halluc-detail">
    <strong>[{{ h.severity | upper }}]</strong> {{ h.claim[:150] }}
    <br><em>{{ h.reasoning[:200] }}</em>
  </div>
  {% endif %}
  {% endfor %}
  {% endif %}

</details>
{% endif %}
{% endfor %}

<!-- ===== METADONNEES ===== -->
<div class="section-sep"></div>
<h2>Metadonnees de l'execution</h2>
<table>
<tr><th>Parametre</th><th>Valeur</th></tr>
<tr><td>Run ID</td><td>{{ run.run_id }}</td></tr>
<tr><td>Version benchmark</td><td>{{ run.metadata.benchmark_version }}</td></tr>
<tr><td>Timestamp</td><td>{{ run.metadata.timestamp_utc }}</td></tr>
<tr><td>Duree totale</td><td>{{ "%.1f"|format(run.metadata.duration_seconds) }}s</td></tr>
<tr><td>Modele juge</td><td>{{ run.metadata.judge_model }}</td></tr>
<tr><td>Temperature juge</td><td>{{ run.metadata.judge_temperature }}</td></tr>
<tr><td>Dataset</td><td>{{ run.metadata.dataset_path }}</td></tr>
<tr><td>Dataset SHA256</td><td><code>{{ run.metadata.dataset_sha256 }}</code></td></tr>
<tr><td>Nombre de taches</td><td>{{ run.metadata.n_tasks }}</td></tr>
<tr><td>Python</td><td>{{ run.metadata.python_version[:30] }}</td></tr>
<tr><td>Plateforme</td><td>{{ run.metadata.platform }}</td></tr>
</table>

<p class="meta" style="margin-top: 2rem; text-align: center;">
  Genere par FrenchLaw Bench v{{ run.metadata.benchmark_version }}
</p>

</body>
</html>
"""


def generate_report(run: BenchmarkRun, output_dir: Path | None = None) -> Path:
    """Genere un rapport HTML et sauvegarde les resultats JSON."""
    out = output_dir or RESULTS_DIR / run.run_id
    out.mkdir(parents=True, exist_ok=True)

    # JSON complet
    json_path = out / "results.json"
    json_path.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # JSON resume (stats seulement, sans les reponses completes pour partage)
    summary_data = {
        "run_id": run.run_id,
        "timestamp": str(run.timestamp),
        "metadata": run.metadata.model_dump(mode="json"),
        "aggregates": [a.model_dump(mode="json") for a in run.aggregates],
        "task_scores": [
            {
                "task_number": r.task_number,
                "task_title": r.task_title,
                "category": r.category,
                "model_id": r.model_id,
                "answer_score": r.answer_score,
                "answer_score_by_dimension": r.answer_score_by_dimension,
                "source_score": r.source_score,
                "hallucination_count": r.hallucination_count,
                "hallucination_severity_counts": r.hallucination_severity_counts,
                "negatif_items_triggered": r.negatif_items_triggered,
                "latency_seconds": r.latency_seconds,
                "cost_usd": r.cost_usd,
                "error": r.error,
            }
            for r in run.task_results
        ],
    }
    summary_path = out / "summary.json"
    summary_path.write_text(
        json.dumps(summary_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # HTML
    html_path = out / "report.html"
    template = Template(_HTML_TEMPLATE)
    html_path.write_text(template.render(run=run), encoding="utf-8")

    return html_path
