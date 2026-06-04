"""Node schemas for all 31 node types organized by ontology module."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Foundation Module (12 nodes)

class Disease(BaseModel):
    """Disease node type."""
    disease_id: str = Field(..., description="Unique disease identifier")
    name: str
    category: str
    icd10_code: Optional[str] = None
    prevalence: Optional[float] = None
    ontology_source: str = "ICD-10"


class Drug(BaseModel):
    """Drug node type."""
    drug_id: str
    name: str
    generic_name: str
    drug_type: Literal["Small Molecule", "Monoclonal Antibody", "Biologic", "Peptide", "ADC", "Gene Therapy"]
    approval_status: Literal["Approved", "Investigational", "Withdrawn", "Phase III"]
    approval_year: Optional[int] = None
    mechanism: Optional[str] = None
    ontology_source: str = "DrugBank"


class Gene(BaseModel):
    """Gene node type."""
    gene_id: str
    symbol: str
    name: str
    chromosome: Optional[str] = None
    function: Optional[str] = None
    ontology_source: str = "HGNC"


class Protein(BaseModel):
    """Protein node type."""
    protein_id: str
    name: str
    uniprot_id: Optional[str] = None
    protein_class: Optional[str] = None
    cellular_location: Optional[str] = None
    ontology_source: str = "UniProt"


class Pathway(BaseModel):
    """Pathway node type."""
    pathway_id: str
    name: str
    kegg_id: Optional[str] = None
    category: Optional[str] = None
    organism: Optional[str] = None
    ontology_source: str = "KEGG"


class BiologicalProcess(BaseModel):
    """Biological Process node type."""
    process_id: str
    name: str
    go_id: Optional[str] = None
    category: Optional[str] = None
    ontology_source: str = "Gene Ontology"


class MolecularFunction(BaseModel):
    """Molecular Function node type."""
    function_id: str
    name: str
    go_id: Optional[str] = None
    category: Optional[str] = None
    ontology_source: str = "Gene Ontology"


class Anatomy(BaseModel):
    """Anatomy node type."""
    anatomy_id: str
    name: str
    uberon_id: Optional[str] = None
    system: Optional[str] = None
    ontology_source: str = "UBERON"


class CellType(BaseModel):
    """Cell Type node type."""
    cell_type_id: str
    name: str
    cell_ontology_id: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    ontology_source: str = "Cell Ontology"


class Phenotype(BaseModel):
    """Phenotype node type."""
    phenotype_id: str
    name: str
    hpo_id: Optional[str] = None
    category: Optional[str] = None
    ontology_source: str = "HPO"


class Biomarker(BaseModel):
    """Biomarker node type."""
    biomarker_id: str
    name: str
    type: str
    measurement_unit: Optional[str] = None
    clinical_significance: Optional[str] = None
    ontology_source: str = "Custom"


class Exposure(BaseModel):
    """Exposure node type."""
    exposure_id: str
    name: str
    exposure_type: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    ontology_source: str = "IARC/WHO"


# Commercial Module (2 nodes)

class RegulatorySubmission(BaseModel):
    """Regulatory Submission node type."""
    submission_id: str
    drug_id: str
    agency: str
    submission_type: str
    status: str
    market: Optional[str] = None
    ontology_source: str = "FDA/EMA"


class ExternalMapping(BaseModel):
    """External Mapping node type."""
    entity_id: str
    entity_type: str
    standard: str
    external_id: str
    confidence: float
    ontology_source: str = "Multi-vocab"


# Clinical Module (3 nodes)

class ClinicalTrial(BaseModel):
    """Clinical Trial node type."""
    trial_id: str
    nct_id: Optional[str] = None
    title: str
    phase: Optional[str] = None
    status: str
    enrollment: Optional[int] = None
    ontology_source: str = "ClinicalTrials.gov"


class AdverseEvent(BaseModel):
    """Adverse Event node type."""
    event_id: str
    name: str
    severity: str
    category: Optional[str] = None
    frequency: Optional[float] = None
    ontology_source: str = "MedDRA"


class ResearchPaper(BaseModel):
    """Research Paper node type."""
    paper_id: str
    title: str
    journal: Optional[str] = None
    publication_date: Optional[date] = None
    doi: Optional[str] = None
    citations: Optional[int] = None
    ontology_source: str = "PubMed"


# Medical Affairs Module (3 nodes)

class AdvisoryBoard(BaseModel):
    """Advisory Board node type."""
    board_id: str
    name: str
    therapeutic_area: str
    meeting_frequency: Optional[str] = None
    member_count: Optional[int] = None
    ontology_source: str = "Custom"


class MedicalInformationRequest(BaseModel):
    """Medical Information Request node type."""
    request_id: str
    requester_type: str
    therapeutic_area: str
    drug_id: Optional[str] = None
    question_category: str
    ontology_source: str = "Custom"


class Researcher(BaseModel):
    """Researcher node type."""
    researcher_id: str
    name: str
    title: Optional[str] = None
    specialization: Optional[str] = None
    h_index: Optional[int] = None
    ontology_source: str = "Custom"


# Patient Module (3 nodes)

class Patient(BaseModel):
    """Patient node type."""
    patient_id: str
    age_group: str
    gender: str
    ethnicity: Optional[str] = None
    diagnosis_year: Optional[int] = None
    consent_status: str
    ontology_source: str = "OMOP CDM"


class PatientOutcome(BaseModel):
    """Patient Outcome node type."""
    outcome_id: str
    patient_id: str
    treatment_id: Optional[str] = None
    response_type: str
    progression_free_months: Optional[float] = None
    ontology_source: str = "CDISC"


class PatientReportedOutcome(BaseModel):
    """Patient Reported Outcome node type."""
    pro_id: str
    patient_id: str
    questionnaire_type: str
    score: float
    assessment_date: date
    ontology_source: str = "PRO-CTCAE"


# Supply/Quality Module (3 nodes)

class ManufacturingSite(BaseModel):
    """Manufacturing Site node type."""
    site_id: str
    name: str
    country: str
    city: str
    gmp_certified: bool
    capacity: Optional[int] = None
    ontology_source: str = "ISO IDMP"


class DrugBatch(BaseModel):
    """Drug Batch node type."""
    batch_id: str
    drug_id: str
    manufacturing_site_id: str
    production_date: date
    quality_status: str
    ontology_source: str = "GS1/DSCSA"


class QualityEvent(BaseModel):
    """Quality Event node type."""
    event_id: str
    batch_id: str
    event_type: str
    severity: str
    capa_id: Optional[str] = None
    ontology_source: str = "ICH Q10"


# Governance Module (2 nodes)

class DataGovernancePolicy(BaseModel):
    """Data Governance Policy node type."""
    policy_id: str
    title: str
    category: str
    scope: str
    effective_date: date
    owner: str
    status: str
    ontology_source: str = "DCAT/ODRL"


class ComplianceRecord(BaseModel):
    """Compliance Record node type."""
    record_id: str
    policy_id: str
    entity_type: str
    entity_id: str
    compliance_status: str
    auditor: str
    ontology_source: str = "Custom"


# GraphRAG Module (3 nodes)

class Entity(BaseModel):
    """Entity node type for graph extraction."""
    entity_id: str
    name: str
    entity_type: str
    source: str
    ontology_source: str = "NCBI Taxonomy"


class Cluster(BaseModel):
    """Cluster node type."""
    cluster_id: str
    name: str
    cluster_type: str
    algorithm: str
    node_count: int
    ontology_source: str = "GraphRAG"


class ClusterSummary(BaseModel):
    """Cluster Summary node type."""
    summary_id: str
    cluster_id: str
    summary_text: str
    key_entities: list[str]
    confidence_score: float
    ontology_source: str = "GraphRAG"


# Organizational Module (1 node)

class Institution(BaseModel):
    """Institution node type."""
    institution_id: str
    name: str
    type: str
    country: str
    city: str
    research_budget_millions: Optional[float] = None
    ontology_source: str = "Custom"
