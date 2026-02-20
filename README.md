# FrenchLaw Bench

Framework d'evaluation quantitative des LLM sur des taches juridiques complexes en **droit francais et europeen**.

Inspire du [BigLaw Bench](https://github.com/harveyai/biglaw-bench) de Harvey AI, adapte au droit civil francais, au contentieux et au droit de l'Union europeenne.

## Pourquoi

Les benchmarks juridiques existants (LegalBench, GreekBarBench) se limitent a des questions fermees ou au droit anglo-saxon. FrenchLaw Bench evalue les LLM sur des taches qui refletent le **travail reellement facture** par les avocats en cabinet : redaction, analyse, conseil strategique, qualification juridique.

## Architecture

```
frenchlaw-bench/
├── src/frenchlaw_bench/       # Package Python
│   ├── models/                # Pydantic models (Task, Rubric, Result)
│   ├── core/                  # Chargement CSV + parsing rubrics
│   ├── scoring/               # LLM-as-Judge, hallucination, sources
│   ├── llm/                   # Client OpenRouter (multi-modele)
│   ├── pipeline/              # Orchestrateur async
│   ├── workflows/             # Cession d'actions (deal points FR)
│   └── reports/               # Generation HTML + JSON
├── data/
│   ├── core/tasks.csv         # 20 taches avec rubrics
│   └── workflows/             # Schema + ground truth
└── tests/                     # Tests unitaires + integration
```

### Composantes

| Composante | Description |
|---|---|
| **FLB-Core** | 20 taches knowledge-only couvrant 3 categories, 12 types, 14 sous-categories |
| **FLB-Workflows** | Extraction structuree de deal points (cession d'actions) |
| **Scoring Engine** | LLM-as-Judge avec rubrics bespoke, detection d'hallucinations, source scoring |

## Categories

| Categorie | Poids | Sous-categories |
|---|---|---|
| Droit Prive | ~40% | Corporate, Contrats, Travail, PI, Bancaire |
| Contentieux | ~35% | Commercial, Administratif, Penal, RGPD, Concurrence FR |
| Droit Europeen | ~25% | UE Institutionnel, CEDH, Concurrence UE, Numerique UE |

## Scoring

Chaque tache possede un **rubric bespoke** structure en 4+1 dimensions :

- **Structure** (1-3 pts) : format attendu (note, assignation, commentaire d'arret...)
- **Style** (0-2 pts) : registre juridique, citations au format FR
- **Substance** (8-20+ pts) : textes applicables, jurisprudence, analyse
- **Methodologie** (0-3 pts) : syllogisme juridique, distinction fait/droit
- **Negatif** : hallucinations (-1pt), hors sujet (-0.5pt), texte abroge (-2pts)

```
Answer Score = (pts positifs gagnes - penalites) / total pts positifs disponibles
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copier `.env.example` vers `.env` et renseigner la cle API :

```bash
cp .env.example .env
# Editer .env avec votre cle OpenRouter
```

## Usage

```bash
# Valider les taches (parsing CSV + rubrics)
flb validate

# Executer le benchmark sur un ou plusieurs modeles
flb run -m google/gemini-2.5-pro -m openai/gpt-4o

# Comparer des runs
flb compare <run_id_1> <run_id_2>
```

### Options

```
flb run -m <model_id>       # Modele OpenRouter a evaluer (repetable)
        -c <N>              # Concurrence max (defaut: 5)
        -o <dir>            # Dossier de sortie
        --tasks-csv <path>  # CSV de taches alternatif
```

## Resultats

Chaque run genere :
- `results/<run_id>/results.json` : resultats detailles (reponses, scores par item, hallucinations)
- `results/<run_id>/report.html` : rapport visuel avec tableaux comparatifs

### Metriques

| Metrique | Description |
|---|---|
| **Answer Score** | % du travail de qualite avocat produit par le modele |
| **Source Score** | % d'assertions correctement attribuees a une source |
| **Hallucination Rate** | % de claims factuels demontrement faux |

## Tests

```bash
pytest tests/ -v
```

## Licence

Proprietary - Roy

---

<p align="center">
  <a href="https://roy.legal">
    <img src="roy-icon-512.png" alt="Roy" width="48" height="48">
  </a>
  <br>
  Propose par <a href="https://roy.legal"><strong>Roy</strong></a>
</p>
