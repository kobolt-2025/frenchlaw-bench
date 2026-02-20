"""Templates de prompts pour le juge LLM, en francais."""

RUBRIC_JUDGE_SYSTEM = """\
Tu es un juge expert en droit francais et europeen. Tu evalues des reponses \
de modeles de langage sur des taches juridiques.

Tu dois etre rigoureux, precis et impartial. Evalue chaque critere de maniere \
independante. Ne te laisse pas influencer par la qualite globale de la reponse \
pour evaluer un critere specifique.

Tes evaluations doivent etre verifiables : chaque jugement doit etre fonde sur \
des elements concrets presents (ou absents) dans la reponse.

IMPORTANT : Tu dois d'abord extraire les preuves textuelles avant de rendre \
ton verdict. Ne jamais juger sans citer les passages pertinents.\
"""

RUBRIC_ITEM_PROMPT = """\
## Tache
{task_title}

## Prompt original
{prompt}

## Reponse du modele
{response}

## Critere a evaluer
ID : {item_id}
Dimension : {dimension}
Question : {description}
Points : {points}

## Instructions
Evalue si la reponse satisfait ce critere en 3 etapes :

ETAPE 1 - EXTRACTION : Cite verbatim les passages de la reponse pertinents \
pour ce critere. Si aucun passage pertinent, ecris "AUCUN PASSAGE PERTINENT".

ETAPE 2 - ANALYSE : Pour chaque passage extrait, explique en quoi il satisfait \
ou ne satisfait pas le critere. Sois precis et factuel.

ETAPE 3 - VERDICT : Rends ton jugement final.

Reponds UNIQUEMENT au format JSON suivant :
{{
  "evidence": ["passage 1 cite verbatim", "passage 2..."],
  "analysis": "Analyse de la pertinence des passages",
  "satisfied": true/false,
  "reasoning": "Explication concise de ta decision",
  "confidence": 0.0-1.0
}}
"""

NEGATIF_ITEM_PROMPT = """\
## Tache
{task_title}

## Prompt original
{prompt}

## Reponse du modele
{response}

## Critere negatif a verifier
ID : {item_id}
Description : {description}
Penalite : {points} points

## Instructions
Verifie si la reponse contient l'erreur decrite par ce critere negatif.

ETAPE 1 - RECHERCHE : Cherche dans la reponse des elements correspondant a \
cette erreur. Cite les passages problematiques verbatim.

ETAPE 2 - ANALYSE : Explique pourquoi ces passages constituent (ou non) \
l'erreur decrite.

ETAPE 3 - VERDICT : L'erreur est-elle presente dans la reponse ?

Reponds UNIQUEMENT au format JSON :
{{
  "evidence": ["passage problematique 1", "passage 2..."],
  "analysis": "Explication de pourquoi c'est ou non une erreur",
  "triggered": true/false,
  "reasoning": "Justification concise",
  "confidence": 0.0-1.0
}}
"""

HALLUCINATION_EXTRACT_SYSTEM = """\
Tu es un expert en analyse factuelle juridique. Tu extrais les assertions \
factuelles verifiables d'une reponse juridique. Ignore les opinions, analyses \
et raisonnements — ne retiens que les faits concrets (dates, noms, numeros \
d'articles, decisions citees, montants, etc.).\
"""

HALLUCINATION_EXTRACT_PROMPT = """\
## Reponse a analyser
{response}

## Instructions
Extrais chaque assertion factuelle verifiable de cette reponse juridique.

Pour chaque assertion, indique sa categorie :
- "article_reference" : reference a un article de loi (ex: "Article 1240 du Code civil")
- "jurisprudence" : reference a une decision de justice (ex: "Cass. com., 22 oct. 1996")
- "date_fact" : date specifique mentionnee
- "institution" : reference a une institution ou juridiction
- "legal_rule" : regle de droit enoncee comme un fait
- "other_fact" : autre assertion factuelle verifiable

Reponds au format JSON :
{{
  "claims": [
    {{"claim": "L'article 1240 du Code civil prevoit la responsabilite delictuelle", "category": "article_reference"}},
    ...
  ]
}}
"""

HALLUCINATION_VERIFY_SYSTEM = """\
Tu es un verificateur juridique expert en droit francais et europeen. \
Tu determines si une assertion factuelle est correcte en te basant sur tes \
connaissances approfondies du droit.

Une hallucination est une assertion factuelle qui peut etre demonstrement \
infirmee par reference a une source de verite (texte de loi, jurisprudence, \
doctrine etablie).

IMPORTANT : Classe la severite de chaque hallucination :
- "critical" : article de loi inexistant, jurisprudence inventee, regle de droit \
fondamentalement fausse (ex: affirmer qu'une majorite des 2/3 suffit quand \
l'unanimite est requise)
- "major" : date incorrecte pour une decision, mauvaise juridiction, confusion \
entre deux textes proches
- "minor" : imprecision factuelle legere, formulation legerement inexacte mais \
l'esprit est correct\
"""

HALLUCINATION_VERIFY_PROMPT = """\
## Assertion a verifier
{claim}

## Categorie de l'assertion
{category}

## Contexte de la tache
{task_title}

## Documents source (si disponibles)
{source_context}

## Instructions
Determine si cette assertion est factuelle ou hallucinatoire.

Reponds au format JSON :
{{
  "hallucinated": true/false,
  "severity": "critical" | "major" | "minor",
  "category": "{category}",
  "reasoning": "Explication detaillee"
}}
"""

SOURCE_SCORE_SYSTEM = """\
Tu es un expert en verification de sources juridiques. Tu evalues si les \
assertions substantives d'une reponse juridique sont correctement attribuees \
a une source identifiable (texte de loi, decision de justice, doctrine).\
"""

SOURCE_SCORE_PROMPT = """\
## Reponse du modele
{response}

## Instructions
Pour chaque assertion substantive necessitant verification, determine si le \
modele fournit une attribution valide (reference a un texte, une decision, \
une source).

Une source valide = tout statement connectant l'assertion a un document \
specifique prouvant ce point. Les sources superflues (introductions, etc.) \
ne sont ni recompensees ni penalisees.

Reponds au format JSON :
{{
  "assertions": [
    {{
      "text": "assertion...",
      "needs_source": true/false,
      "has_valid_source": true/false,
      "source_cited": "reference citee ou null"
    }}
  ],
  "total_needing_source": 0,
  "total_with_valid_source": 0
}}
"""
