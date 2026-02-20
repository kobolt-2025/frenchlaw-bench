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
│   ├── llm/                   # Client OpenRouter (multi-modele, provider routing)
│   ├── pipeline/              # Orchestrateur async parallele
│   ├── workflows/             # Cession d'actions (deal points FR)
│   ├── reports/               # Generation HTML + JSON + summary
│   └── json_utils.py          # Parser JSON robuste pour reponses LLM
├── data/
│   ├── core/tasks.csv         # 20 taches avec rubrics
│   └── workflows/             # Schema + ground truth
└── tests/                     # Tests unitaires (50 tests)
```

### Composantes

| Composante | Description |
|---|---|
| **FLB-Core** | 20 taches knowledge-only couvrant 3 categories, 12 types, 14 sous-categories |
| **FLB-Workflows** | Extraction structuree de deal points (cession d'actions) |
| **Scoring Engine** | LLM-as-Judge evidence-anchored, detection d'hallucinations avec severite, scoring negatif, source scoring |

## Categories

| Categorie | Poids | Sous-categories |
|---|---|---|
| Droit Prive | ~40% | Corporate, Contrats, Travail, PI, Bancaire |
| Contentieux | ~35% | Commercial, Administratif, Penal, RGPD, Concurrence FR |
| Droit Europeen | ~25% | UE Institutionnel, CEDH, Concurrence UE, Numerique UE |

## Scoring (v0.2.0)

Chaque tache possede un **rubric bespoke** structure en 4+1 dimensions :

- **Structure** (1-3 pts, poids 1.0x) : format attendu (note, assignation, commentaire d'arret...)
- **Style** (0-2 pts, poids 0.8x) : registre juridique, citations au format FR
- **Substance** (8-20+ pts, poids 1.5x) : textes applicables, jurisprudence, analyse
- **Methodologie** (0-3 pts, poids 1.3x) : syllogisme juridique, distinction fait/droit
- **Negatif** : hallucinations (-1pt), hors sujet (-0.5pt), texte abroge (-2pts) — evalue par le juge LLM

### Evidence-Anchored Judging

Inspire de RULERS (ICLR 2025), chaque critere est evalue en 3 etapes :
1. **Extraction** : passages verbatim de la reponse
2. **Analyse** : mise en correspondance preuves / critere
3. **Verdict** : satisfied + confidence [0-1]

### Detection d'hallucinations

Pipeline en 2 etapes inspire de HalluDetect (EMNLP 2025) :
1. Extraction des claims factuels avec categories (article, jurisprudence, date, etc.)
2. Verification parallele avec classification de severite :
   - **Critical** (2 pts) : article invente, jurisprudence fictive
   - **Major** (1 pt) : mauvaise juridiction, date incorrecte
   - **Minor** (0.3 pt) : imprecision legere

### Formule de score

```
Score = max(0, (points ponderes * confiance - penalite hallucinations - penalite negatif) / total pondere)
```

Score clamp a [0, 1]. Penalite d'hallucination plafonnee au total des points positifs.

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

# Executer le benchmark
flb run -m google/gemini-2.5-pro -m openai/gpt-4o

# Avec provider specifique et modele juge custom
flb run -m openai/gpt-oss-120b:nitro -p Cerebras -q fp16 -j google/gemini-3-flash-preview

# Mode verbose
flb -v run -m anthropic/claude-sonnet-4-20250514

# Comparer des runs
flb compare <run_id_1> <run_id_2>
```

### Options

```
flb run -m <model_id>       # Modele OpenRouter a evaluer (repetable)
        -c <N>              # Concurrence max (defaut: 5)
        -o <dir>            # Dossier de sortie
        -j <model_id>       # Modele juge (defaut: env JUDGE_MODEL)
        -p <provider>       # Provider OpenRouter (ex: Cerebras, Together)
        -q <quantization>   # Quantization (ex: fp16, int8, bf16)
        --tasks-csv <path>  # CSV de taches alternatif
```

## Resultats

Chaque run genere :
- `results/<run_id>/results.json` : resultats detailles (reponses, scores par item, hallucinations)
- `results/<run_id>/summary.json` : metriques agregees uniquement
- `results/<run_id>/report.html` : rapport visuel avec cartes, barres, details expandables

### Metriques

| Metrique | Description |
|---|---|
| **Answer Score** | % du travail de qualite avocat, pondere par dimension et confiance |
| **Source Score** | % d'assertions correctement attribuees a une source |
| **Hallucination Rate** | % de claims factuels demontrement faux |
| **IC 95%** | Intervalle de confiance bootstrap (1000 resamples) |
| **Scores par dimension** | Structure, Style, Substance, Methodologie |
| **Scores par categorie** | Droit Prive, Contentieux, Droit Europeen |
| **Latence** | P50, P95, P99, min/max/std |
| **Tokens** | Total, moyenne par tache |
| **Cout** | Estimation USD basee sur les tarifs OpenRouter |

### Reproductibilite

Chaque run enregistre :
- SHA256 du dataset
- Version Python et plateforme
- Modele juge et temperature
- Duree totale d'execution

## Tests

```bash
pytest tests/ -v    # 50 tests
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
