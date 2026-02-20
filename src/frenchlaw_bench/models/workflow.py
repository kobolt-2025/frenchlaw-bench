"""Modèle pour le workflow Cession d'Actions (équivalent SPA Deal Points)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Entite(BaseModel):
    nom: str = ""
    forme_juridique: str = ""
    rcs: str = ""
    siege_social: str = ""


class ActionsCedees(BaseModel):
    nombre: int | None = None
    pourcentage: float | None = None
    categorie: str = ""
    valeur_nominale: float | None = None


class PrixCession(BaseModel):
    montant: float | None = None
    prix_par_action: float | None = None
    modalites_paiement: str = ""
    sequestre: bool | None = None
    montant_sequestre: float | None = None


class ComplementPrix(BaseModel):
    earn_out: bool | None = None
    criteres: str = ""
    plafond: float | None = None
    duree: str = ""


class GarantieActifPassif(BaseModel):
    duree: str = ""
    plafond: float | None = None
    franchise: float | None = None
    type_franchise: str = Field(default="", description="absolue, relative, à première demande")
    exclusions: list[str] = Field(default_factory=list)


class ClauseNonConcurrence(BaseModel):
    duree: str = ""
    perimetre_geographique: str = ""
    activite: str = ""
    contrepartie: str = ""


class CessionActions(BaseModel):
    """Schema complet pour l'extraction de deal points d'une cession d'actions."""

    date_signature: str = ""
    cessionnaire: Entite = Field(default_factory=Entite)
    cedant: Entite = Field(default_factory=Entite)
    societe_cible: Entite = Field(default_factory=Entite)
    actions_cedees: ActionsCedees = Field(default_factory=ActionsCedees)
    prix_de_cession: PrixCession = Field(default_factory=PrixCession)
    complement_de_prix: ComplementPrix = Field(default_factory=ComplementPrix)
    garantie_actif_passif: GarantieActifPassif = Field(default_factory=GarantieActifPassif)
    clause_non_concurrence: ClauseNonConcurrence = Field(default_factory=ClauseNonConcurrence)
    conditions_suspensives: list[str] = Field(default_factory=list)
    droit_applicable: str = Field(default="Droit français")
    juridiction_competente: str = ""
    frais_droits_enregistrement: str = ""
    repartition_frais: str = ""
