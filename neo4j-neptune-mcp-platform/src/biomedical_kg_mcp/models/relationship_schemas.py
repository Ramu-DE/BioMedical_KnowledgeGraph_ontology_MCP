"""Relationship schemas for all 37 relationship types."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Relationship(BaseModel):
    """Base relationship with common properties."""
    source_id: str
    target_id: str


# Foundation relationships (18)

class DrugTreatsDisease(Relationship):
    """DRUG_TREATS_DISEASE relationship."""
    efficacy_rate: Optional[float] = None
    approval_year: Optional[int] = None


class DrugTargetsProtein(Relationship):
    """DRUG_TARGETS_PROTEIN relationship."""
    binding_affinity: Optional[float] = None


class GeneAssociatedWithDisease(Relationship):
    """GENE_ASSOCIATED_WITH_DISEASE relationship."""
    association_score: Optional[float] = None


class GeneHasMolecularFunction(Relationship):
    """GENE_HAS_MOLECULAR_FUNCTION relationship."""
    evidence_code: Optional[str] = None


class GeneInvolvedInBiologicalProcess(Relationship):
    """GENE_INVOLVED_IN_BIOLOGICAL_PROCESS relationship."""
    evidence_code: Optional[str] = None


class GeneParticipatesInPathway(Relationship):
    """GENE_PARTICIPATES_IN_PATHWAY relationship."""
    role: Optional[str] = None


class ProteinInvolvedInPathway(Relationship):
    """PROTEIN_INVOLVED_IN_PATHWAY relationship."""
    role: Optional[str] = None


class ProteinInvolvedInBiologicalProcess(Relationship):
    """PROTEIN_INVOLVED_IN_BIOLOGICAL_PROCESS relationship."""
    evidence_code: Optional[str] = None


class ProteinHasMolecularFunction(Relationship):
    """PROTEIN_HAS_MOLECULAR_FUNCTION relationship."""
    evidence_code: Optional[str] = None


class ProteinExpressedInAnatomy(Relationship):
    """PROTEIN_EXPRESSED_IN_ANATOMY relationship."""
    expression_level: Optional[str] = None


class DiseaseAffectsAnatomy(Relationship):
    """DISEASE_AFFECTS_ANATOMY relationship."""
    severity: Optional[str] = None


class DiseaseHasPhenotype(Relationship):
    """DISEASE_HAS_PHENOTYPE relationship."""
    frequency: Optional[float] = None


class DiseaseInvolvesCellType(Relationship):
    """DISEASE_INVOLVES_CELL_TYPE relationship."""
    involvement_type: Optional[str] = None


class CellTypeFoundInAnatomy(Relationship):
    """CELL_TYPE_FOUND_IN_ANATOMY relationship."""
    abundance: Optional[str] = None


class PathwayInvolvesBiologicalProcess(Relationship):
    """PATHWAY_INVOLVES_BIOLOGICAL_PROCESS relationship."""
    stage: Optional[str] = None


class PhenotypeAssociatedWithGene(Relationship):
    """PHENOTYPE_ASSOCIATED_WITH_GENE relationship."""
    association_score: Optional[float] = None


class ExposureAffectsGene(Relationship):
    """EXPOSURE_AFFECTS_GENE relationship."""
    effect_type: Optional[str] = None


class ExposureIncreasesRiskDisease(Relationship):
    """EXPOSURE_INCREASES_RISK_DISEASE relationship."""
    relative_risk: Optional[float] = None


# Clinical relationships (6)

class BiomarkerPredictsResponse(Relationship):
    """BIOMARKER_PREDICTS_RESPONSE relationship."""
    predictive_value: Optional[float] = None


class EntityAssociatedWithDisease(Relationship):
    """ENTITY_ASSOCIATED_WITH_DISEASE relationship."""
    confidence: Optional[float] = None


class TrialInvestigatesDrug(Relationship):
    """TRIAL_INVESTIGATES_DRUG relationship."""
    arm: Optional[str] = None


class TrialStudiesDisease(Relationship):
    """TRIAL_STUDIES_DISEASE relationship."""
    indication: Optional[str] = None


class TrialReportsAdverseEvent(Relationship):
    """TRIAL_REPORTS_ADVERSE_EVENT relationship."""
    incidence_rate: Optional[float] = None


class InstitutionSponsorsTrial(Relationship):
    """INSTITUTION_SPONSORS_TRIAL relationship."""
    funding_amount: Optional[float] = None


# Research relationships (4)

class PaperMentionsDisease(Relationship):
    """PAPER_MENTIONS_DISEASE relationship."""
    mention_count: Optional[int] = None


class PaperMentionsDrug(Relationship):
    """PAPER_MENTIONS_DRUG relationship."""
    mention_count: Optional[int] = None


class PaperAuthoredBy(Relationship):
    """PAPER_AUTHORED_BY relationship."""
    author_position: Optional[int] = None


class ResearcherAffiliatedWith(Relationship):
    """RESEARCHER_AFFILIATED_WITH relationship."""
    role: Optional[str] = None


# Medical Affairs relationships (1)

class ResearcherAdvisesBoard(Relationship):
    """RESEARCHER_ADVISES_BOARD relationship."""
    appointment_date: Optional[str] = None


# Patient relationships (2)

class PatientEnrolledInTrial(Relationship):
    """PATIENT_ENROLLED_IN_TRIAL relationship."""
    enrollment_date: Optional[str] = None
    arm: Optional[str] = None


class PatientHasOutcome(Relationship):
    """PATIENT_HAS_OUTCOME relationship."""
    assessment_date: Optional[str] = None


# Supply/Quality relationships (2)

class DrugManufacturedAt(Relationship):
    """DRUG_MANUFACTURED_AT relationship."""
    start_date: Optional[str] = None


class BatchProducedForDrug(Relationship):
    """BATCH_PRODUCED_FOR_DRUG relationship."""
    quantity: Optional[int] = None


# GraphRAG relationships (2)

class NodeBelongsToCluster(Relationship):
    """NODE_BELONGS_TO_CLUSTER relationship."""
    membership_score: Optional[float] = None


class ClusterHasSummary(Relationship):
    """CLUSTER_HAS_SUMMARY relationship."""
    generated_at: Optional[str] = None


# Governance relationships (2)

class PolicyGovernsEntity(Relationship):
    """POLICY_GOVERNS_ENTITY relationship with enforcement level."""
    enforcement_level: Literal["Required", "Recommended", "Optional"] = Field(
        ..., description="Policy enforcement level"
    )


class SubmissionForDrug(Relationship):
    """SUBMISSION_FOR_DRUG relationship."""
    submission_date: Optional[str] = None


# Relationship type registry

RELATIONSHIP_TYPES = {
    "DRUG_TREATS_DISEASE": DrugTreatsDisease,
    "DRUG_TARGETS_PROTEIN": DrugTargetsProtein,
    "GENE_ASSOCIATED_WITH_DISEASE": GeneAssociatedWithDisease,
    "GENE_HAS_MOLECULAR_FUNCTION": GeneHasMolecularFunction,
    "GENE_INVOLVED_IN_BIOLOGICAL_PROCESS": GeneInvolvedInBiologicalProcess,
    "GENE_PARTICIPATES_IN_PATHWAY": GeneParticipatesInPathway,
    "PROTEIN_INVOLVED_IN_PATHWAY": ProteinInvolvedInPathway,
    "PROTEIN_INVOLVED_IN_BIOLOGICAL_PROCESS": ProteinInvolvedInBiologicalProcess,
    "PROTEIN_HAS_MOLECULAR_FUNCTION": ProteinHasMolecularFunction,
    "PROTEIN_EXPRESSED_IN_ANATOMY": ProteinExpressedInAnatomy,
    "DISEASE_AFFECTS_ANATOMY": DiseaseAffectsAnatomy,
    "DISEASE_HAS_PHENOTYPE": DiseaseHasPhenotype,
    "DISEASE_INVOLVES_CELL_TYPE": DiseaseInvolvesCellType,
    "CELL_TYPE_FOUND_IN_ANATOMY": CellTypeFoundInAnatomy,
    "PATHWAY_INVOLVES_BIOLOGICAL_PROCESS": PathwayInvolvesBiologicalProcess,
    "PHENOTYPE_ASSOCIATED_WITH_GENE": PhenotypeAssociatedWithGene,
    "EXPOSURE_AFFECTS_GENE": ExposureAffectsGene,
    "EXPOSURE_INCREASES_RISK_DISEASE": ExposureIncreasesRiskDisease,
    "BIOMARKER_PREDICTS_RESPONSE": BiomarkerPredictsResponse,
    "ENTITY_ASSOCIATED_WITH_DISEASE": EntityAssociatedWithDisease,
    "TRIAL_INVESTIGATES_DRUG": TrialInvestigatesDrug,
    "TRIAL_STUDIES_DISEASE": TrialStudiesDisease,
    "TRIAL_REPORTS_ADVERSE_EVENT": TrialReportsAdverseEvent,
    "INSTITUTION_SPONSORS_TRIAL": InstitutionSponsorsTrial,
    "PAPER_MENTIONS_DISEASE": PaperMentionsDisease,
    "PAPER_MENTIONS_DRUG": PaperMentionsDrug,
    "PAPER_AUTHORED_BY": PaperAuthoredBy,
    "RESEARCHER_AFFILIATED_WITH": ResearcherAffiliatedWith,
    "RESEARCHER_ADVISES_BOARD": ResearcherAdvisesBoard,
    "PATIENT_ENROLLED_IN_TRIAL": PatientEnrolledInTrial,
    "PATIENT_HAS_OUTCOME": PatientHasOutcome,
    "DRUG_MANUFACTURED_AT": DrugManufacturedAt,
    "BATCH_PRODUCED_FOR_DRUG": BatchProducedForDrug,
    "NODE_BELONGS_TO_CLUSTER": NodeBelongsToCluster,
    "CLUSTER_HAS_SUMMARY": ClusterHasSummary,
    "POLICY_GOVERNS_ENTITY": PolicyGovernsEntity,
    "SUBMISSION_FOR_DRUG": SubmissionForDrug,
}
