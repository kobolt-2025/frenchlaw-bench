"""Enums pour les catégories, sous-catégories et types de tâches."""

from __future__ import annotations

from enum import Enum


class Category(str, Enum):
    DROIT_PRIVE = "Droit Privé"
    CONTENTIEUX = "Contentieux"
    DROIT_EUROPEEN = "Droit Européen"


class SubCategory(str, Enum):
    # Droit Privé
    CORPORATE_SOCIETES = "Corporate / Sociétés"
    CONTRATS = "Contrats"
    TRAVAIL = "Travail"
    PROPRIETE_INTELLECTUELLE = "Propriété intellectuelle"
    BANCAIRE_FINANCIER = "Bancaire & Financier"
    # Contentieux
    COMMERCIAL = "Commercial"
    ADMINISTRATIF = "Administratif"
    PENAL_AFFAIRES = "Pénal des affaires"
    RGPD_DONNEES = "RGPD / Données"
    CONCURRENCE_FR = "Concurrence FR"
    # Droit Européen
    UE_INSTITUTIONNEL = "UE Institutionnel"
    CEDH = "CEDH"
    CONCURRENCE_UE = "Concurrence UE"
    NUMERIQUE_UE = "Numérique UE"


class TaskType(str, Enum):
    CONSEIL_STRATEGIQUE = "Conseil stratégique"
    REDACTION = "Rédaction"
    RECHERCHE_JURIDIQUE = "Recherche juridique"
    AUDIT_DUE_DILIGENCE = "Audit / Due diligence"
    RISQUES_CONFORMITE = "Risques & Conformité"
    STRATEGIE_NEGOCIATION = "Stratégie de négociation"
    ANALYSE_DOCUMENTS = "Analyse de documents"
    ANALYSE_JURISPRUDENCE = "Analyse de jurisprudence"
    GESTION_DOSSIER = "Gestion de dossier"
    PREPARATION_CONTENTIEUSE = "Préparation contentieuse"
    QUALIFICATION_JURIDIQUE = "Qualification juridique"
    STRUCTURATION_OPERATION = "Structuration d'opération"


class Dimension(str, Enum):
    STRUCTURE = "Structure"
    STYLE = "Style"
    SUBSTANCE = "Substance"
    METHODOLOGIE = "Méthodologie"
    NEGATIF = "Négatif"
