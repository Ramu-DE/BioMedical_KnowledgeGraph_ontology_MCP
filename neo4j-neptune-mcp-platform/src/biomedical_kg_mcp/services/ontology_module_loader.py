"""Ontology Module Loader for 7 OWL Modules.

Manages the 7 biomedical ontology modules:
- Foundation: Core BFO/RO upper ontology
- Commercial: Drug development, market access, pricing
- Clinical: Trials, outcomes, adverse events
- Medical Affairs: Publications, KOLs, advisory boards
- Patient: Patient-reported outcomes, support programs
- Supply/Quality: Manufacturing, batches, quality events
- Governance: Data policies, compliance, audit trails
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

logger = logging.getLogger(__name__)

BIOMEDKG = Namespace("https://biomedkg.org/ontology/")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
RO = Namespace("http://purl.obolibrary.org/obo/RO_")


class OntologyModuleLoader:
    """Loads and manages 7 OWL ontology modules for biomedical KG."""
    
    MODULES = {
        "foundation": {
            "uri": "https://biomedkg.org/ontology/foundation.ttl",
            "imports": ["bfo2020", "ro"],
            "classes": ["Entity", "Process", "Quality", "Role", "Disposition"],
            "description": "Foundation ontology based on BFO 2020 and RO"
        },
        "commercial": {
            "uri": "https://biomedkg.org/ontology/commercial.ttl",
            "imports": ["foundation"],
            "classes": ["Drug", "Batch", "ManufacturingSite", "RegulatorySubmission"],
            "description": "Commercial domain: drugs, manufacturing, regulatory"
        },
        "clinical": {
            "uri": "https://biomedkg.org/ontology/clinical.ttl",
            "imports": ["foundation"],
            "classes": ["ClinicalTrial", "Patient", "AdverseEvent", "Outcome"],
            "description": "Clinical domain: trials, patients, safety"
        },
        "medical_affairs": {
            "uri": "https://biomedkg.org/ontology/medical-affairs.ttl",
            "imports": ["foundation"],
            "classes": ["ResearchPaper", "Researcher", "AdvisoryBoard"],
            "description": "Medical affairs: publications, KOLs, advisory boards"
        },
        "patient": {
            "uri": "https://biomedkg.org/ontology/patient.ttl",
            "imports": ["foundation", "clinical"],
            "classes": ["PatientOutcome", "PatientReportedOutcome", "Biomarker"],
            "description": "Patient domain: outcomes, PROs, biomarkers"
        },
        "supply_quality": {
            "uri": "https://biomedkg.org/ontology/supply-quality.ttl",
            "imports": ["foundation", "commercial"],
            "classes": ["QualityEvent", "Batch", "ManufacturingSite"],
            "description": "Supply chain and quality management"
        },
        "governance": {
            "uri": "https://biomedkg.org/ontology/governance.ttl",
            "imports": ["foundation"],
            "classes": ["DataGovernancePolicy", "ComplianceRecord", "AuditTrail"],
            "description": "Data governance, compliance, audit"
        }
    }
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).parent.parent / "ontologies"
        self.graphs: Dict[str, Graph] = {}
    
    def generate_module(self, module_name: str) -> Graph:
        """Generate OWL module programmatically."""
        if module_name not in self.MODULES:
            raise ValueError(f"Unknown module: {module_name}")
        
        meta = self.MODULES[module_name]
        g = Graph()
        
        # Bind namespaces
        g.bind("biomedkg", BIOMEDKG)
        g.bind("bfo", BFO)
        g.bind("ro", RO)
        g.bind("owl", OWL)
        g.bind("skos", SKOS)
        
        # Ontology declaration
        ontology_iri = URIRef(meta["uri"])
        g.add((ontology_iri, RDF.type, OWL.Ontology))
        g.add((ontology_iri, RDFS.label, Literal(f"{module_name.title()} Ontology")))
        g.add((ontology_iri, RDFS.comment, Literal(meta["description"])))
        
        # Imports
        for imp in meta["imports"]:
            if imp in self.MODULES:
                g.add((ontology_iri, OWL.imports, URIRef(self.MODULES[imp]["uri"])))
            elif imp == "bfo2020":
                g.add((ontology_iri, OWL.imports, URIRef("http://purl.obolibrary.org/obo/bfo/2020/bfo.owl")))
            elif imp == "ro":
                g.add((ontology_iri, OWL.imports, URIRef("http://purl.obolibrary.org/obo/ro.owl")))
        
        # Class definitions
        for cls_name in meta["classes"]:
            cls_iri = BIOMEDKG[cls_name]
            g.add((cls_iri, RDF.type, OWL.Class))
            g.add((cls_iri, RDFS.label, Literal(cls_name)))
            g.add((cls_iri, RDFS.isDefinedBy, ontology_iri))
        
        # Add domain-specific properties
        self._add_module_properties(g, module_name, ontology_iri)
        
        return g
    
    def _add_module_properties(self, g: Graph, module: str, ontology_iri: URIRef):
        """Add module-specific object/data properties."""
        
        if module == "clinical":
            # hasTrial, enrolledIn, reportsAdverseEvent
            props = [
                ("enrolledIn", "Patient", "ClinicalTrial"),
                ("reportsAdverseEvent", "ClinicalTrial", "AdverseEvent"),
                ("hasOutcome", "Patient", "Outcome")
            ]
            for prop_name, domain, range_cls in props:
                prop_iri = BIOMEDKG[prop_name]
                g.add((prop_iri, RDF.type, OWL.ObjectProperty))
                g.add((prop_iri, RDFS.label, Literal(prop_name)))
                g.add((prop_iri, RDFS.domain, BIOMEDKG[domain]))
                g.add((prop_iri, RDFS.range, BIOMEDKG[range_cls]))
                g.add((prop_iri, RDFS.isDefinedBy, ontology_iri))
        
        elif module == "commercial":
            props = [
                ("manufacturedAt", "Drug", "ManufacturingSite"),
                ("hasRegulatory", "Drug", "RegulatorySubmission"),
                ("producedBatch", "ManufacturingSite", "Batch")
            ]
            for prop_name, domain, range_cls in props:
                prop_iri = BIOMEDKG[prop_name]
                g.add((prop_iri, RDF.type, OWL.ObjectProperty))
                g.add((prop_iri, RDFS.label, Literal(prop_name)))
                g.add((prop_iri, RDFS.domain, BIOMEDKG[domain]))
                g.add((prop_iri, RDFS.range, BIOMEDKG[range_cls]))
                g.add((prop_iri, RDFS.isDefinedBy, ontology_iri))
        
        elif module == "medical_affairs":
            props = [
                ("authored", "Researcher", "ResearchPaper"),
                ("advisesBoard", "Researcher", "AdvisoryBoard"),
                ("mentions", "ResearchPaper", "Drug")
            ]
            for prop_name, domain, range_cls in props:
                prop_iri = BIOMEDKG[prop_name]
                g.add((prop_iri, RDF.type, OWL.ObjectProperty))
                g.add((prop_iri, RDFS.label, Literal(prop_name)))
                g.add((prop_iri, RDFS.domain, BIOMEDKG[domain]))
                g.add((prop_iri, RDFS.range, BIOMEDKG[range_cls]))
                g.add((prop_iri, RDFS.isDefinedBy, ontology_iri))
    
    def load_module(self, module_name: str) -> Graph:
        """Load or generate module graph."""
        if module_name in self.graphs:
            return self.graphs[module_name]
        
        # Try to load from file
        module_path = self.base_path / f"{module_name}.ttl"
        if module_path.exists():
            g = Graph()
            g.parse(module_path, format="turtle")
            logger.info(f"Loaded {module_name} from file: {len(g)} triples")
        else:
            # Generate programmatically
            g = self.generate_module(module_name)
            logger.info(f"Generated {module_name}: {len(g)} triples")
            
            # Save for future use
            self.base_path.mkdir(parents=True, exist_ok=True)
            g.serialize(destination=module_path, format="turtle")
        
        self.graphs[module_name] = g
        return g
    
    def load_all_modules(self) -> Dict[str, Graph]:
        """Load all 7 modules."""
        for module_name in self.MODULES:
            self.load_module(module_name)
        
        return self.graphs
    
    def get_merged_graph(self, modules: Optional[List[str]] = None) -> Graph:
        """Merge multiple modules into single graph."""
        if modules is None:
            modules = list(self.MODULES.keys())
        
        merged = Graph()
        for module in modules:
            g = self.load_module(module)
            merged += g
        
        logger.info(f"Merged {len(modules)} modules: {len(merged)} triples")
        return merged
    
    def export_for_ontosphere(self, modules: Optional[List[str]] = None) -> str:
        """Export modules as Turtle for Ontosphere loading."""
        graph = self.get_merged_graph(modules)
        return graph.serialize(format="turtle")
    
    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """Get metadata about a module."""
        if module_name not in self.MODULES:
            raise ValueError(f"Unknown module: {module_name}")
        
        meta = self.MODULES[module_name].copy()
        
        # Add triple count if loaded
        if module_name in self.graphs:
            meta["triple_count"] = len(self.graphs[module_name])
        
        return meta
