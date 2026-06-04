"""
Ontology Module Manager

Manages 7 OWL ontology modules and provides mapping services.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class OntologyModule(BaseModel):
    """Ontology module definition."""
    name: str
    namespace: str
    version: str
    node_types: List[str]
    description: str


class OntologyClass(BaseModel):
    """Ontology class definition."""
    name: str
    namespace: str
    properties: List[str]
    cardinality: Dict[str, str]
    parent_classes: List[str]


class ColumnMapping(BaseModel):
    """Column to ontology property mapping."""
    column_name: str
    property_name: str
    confidence: float


class OntologyManager:
    """Manages biomedical knowledge graph ontology modules."""

    def __init__(self):
        self.modules = self._init_modules()
        self.base_namespace = "https://biomedkg.org/ontology/"

    def _init_modules(self) -> Dict[str, OntologyModule]:
        """Initialize 7 ontology modules."""
        return {
            "Foundation": OntologyModule(
                name="Foundation",
                namespace=f"{self.base_namespace}Foundation/",
                version="1.0.0",
                node_types=[
                    "Disease", "Drug", "Gene", "Protein", "Pathway",
                    "BiologicalProcess", "MolecularFunction", "Anatomy",
                    "CellType", "Phenotype", "Biomarker", "Exposure"
                ],
                description="Core biomedical entities"
            ),
            "Commercial": OntologyModule(
                name="Commercial",
                namespace=f"{self.base_namespace}Commercial/",
                version="1.0.0",
                node_types=["RegulatorySubmission", "ExternalMapping"],
                description="Commercial and regulatory entities"
            ),
            "Clinical": OntologyModule(
                name="Clinical",
                namespace=f"{self.base_namespace}Clinical/",
                version="1.0.0",
                node_types=["ClinicalTrial", "AdverseEvent", "ResearchPaper"],
                description="Clinical research entities"
            ),
            "Medical_Affairs": OntologyModule(
                name="Medical_Affairs",
                namespace=f"{self.base_namespace}MedicalAffairs/",
                version="1.0.0",
                node_types=["AdvisoryBoard", "MedicalInformationRequest", "Researcher"],
                description="Medical affairs entities"
            ),
            "Patient": OntologyModule(
                name="Patient",
                namespace=f"{self.base_namespace}Patient/",
                version="1.0.0",
                node_types=["Patient", "PatientOutcome", "PatientReportedOutcome"],
                description="Patient-related entities"
            ),
            "Supply_Quality": OntologyModule(
                name="Supply_Quality",
                namespace=f"{self.base_namespace}SupplyQuality/",
                version="1.0.0",
                node_types=["ManufacturingSite", "DrugBatch", "QualityEvent"],
                description="Supply chain and quality entities"
            ),
            "Governance": OntologyModule(
                name="Governance",
                namespace=f"{self.base_namespace}Governance/",
                version="1.0.0",
                node_types=["DataGovernancePolicy", "ComplianceRecord"],
                description="Data governance entities"
            ),
        }

    def list_modules(self) -> List[OntologyModule]:
        """List all ontology modules."""
        return list(self.modules.values())

    def get_class(self, entity_type: str) -> Optional[OntologyClass]:
        """
        Get ontology class definition.
        
        Args:
            entity_type: Entity type (e.g., "Drug", "Disease")
            
        Returns:
            OntologyClass definition
        """
        # Find module containing entity type
        module = None
        for mod in self.modules.values():
            if entity_type in mod.node_types:
                module = mod
                break
        
        if not module:
            return None
        
        # Return class definition (simplified)
        return OntologyClass(
            name=entity_type,
            namespace=module.namespace,
            properties=self._get_properties(entity_type),
            cardinality=self._get_cardinality(entity_type),
            parent_classes=["Entity"],
        )

    def map_columns(
        self, columns: List[str], ontology_module: str, llm_service=None
    ) -> List[ColumnMapping]:
        """
        Map CSV columns to ontology properties.
        
        Args:
            columns: Column names
            ontology_module: Target ontology module
            llm_service: Optional LLM service for intelligent mapping
            
        Returns:
            List of column mappings
        """
        mappings = []
        
        for column in columns:
            # Simple rule-based mapping
            property_name = self._infer_property(column)
            
            mappings.append(ColumnMapping(
                column_name=column,
                property_name=property_name,
                confidence=0.8  # Would use LLM for better confidence
            ))
        
        return mappings

    def _get_properties(self, entity_type: str) -> List[str]:
        """Get properties for entity type."""
        # Common properties
        common = ["id", "name", "description", "created_at", "updated_at"]
        
        # Type-specific properties
        specific = {
            "Drug": ["drug_type", "approval_status", "mechanism_of_action"],
            "Disease": ["disease_category", "icd10_code", "prevalence"],
            "Gene": ["gene_symbol", "chromosome", "gene_type"],
            "ClinicalTrial": ["nct_id", "phase", "status", "enrollment"],
        }
        
        return common + specific.get(entity_type, [])

    def _get_cardinality(self, entity_type: str) -> Dict[str, str]:
        """Get property cardinality constraints."""
        return {
            "id": "1..1",      # Required, single
            "name": "1..1",    # Required, single
            "description": "0..1",  # Optional, single
        }

    def _infer_property(self, column_name: str) -> str:
        """Infer ontology property from column name."""
        # Simple normalization
        normalized = column_name.lower().replace(" ", "_").replace("-", "_")
        
        # Common mappings
        mappings = {
            "id": "id",
            "identifier": "id",
            "name": "name",
            "title": "name",
            "desc": "description",
            "description": "description",
            "type": "type",
            "category": "category",
            "status": "status",
        }
        
        return mappings.get(normalized, normalized)
