"""Ontosphere Startup Configuration Generator.

Generates pre-configured Ontosphere URLs for different use cases:
- Knowledge engineer: all 7 modules + BFO/RO
- Clinical researcher: clinical + patient modules
- Commercial analyst: commercial + supply/quality modules
- Data governance: governance module
"""

from typing import List, Optional, Dict
from urllib.parse import urlencode, quote
from dataclasses import dataclass


@dataclass
class OntosphereConfig:
    """Configuration for Ontosphere startup URL."""
    modules: List[str]
    base_ontologies: List[str]
    rdf_url: Optional[str] = None
    load_imports: bool = True
    description: str = ""


class OntosphereConfigGenerator:
    """Generate pre-configured Ontosphere URLs for different personas."""
    
    BASE_URL = "https://thhanke.github.io/ontosphere/"
    
    MODULE_URLS = {
        "foundation": "https://biomedkg.org/ontology/foundation.ttl",
        "commercial": "https://biomedkg.org/ontology/commercial.ttl",
        "clinical": "https://biomedkg.org/ontology/clinical.ttl",
        "medical_affairs": "https://biomedkg.org/ontology/medical-affairs.ttl",
        "patient": "https://biomedkg.org/ontology/patient.ttl",
        "supply_quality": "https://biomedkg.org/ontology/supply-quality.ttl",
        "governance": "https://biomedkg.org/ontology/governance.ttl"
    }
    
    PERSONAS = {
        "knowledge_engineer": OntosphereConfig(
            modules=["foundation", "commercial", "clinical", "medical_affairs", 
                    "patient", "supply_quality", "governance"],
            base_ontologies=["bfo2020", "ro", "foaf"],
            description="Full ontology suite for knowledge engineers"
        ),
        "clinical_researcher": OntosphereConfig(
            modules=["foundation", "clinical", "patient"],
            base_ontologies=["bfo2020", "foaf"],
            description="Clinical trials and patient outcomes"
        ),
        "commercial_analyst": OntosphereConfig(
            modules=["foundation", "commercial", "supply_quality"],
            base_ontologies=["bfo2020"],
            description="Drug development and supply chain"
        ),
        "medical_affairs": OntosphereConfig(
            modules=["foundation", "medical_affairs"],
            base_ontologies=["bfo2020", "foaf", "dcterms"],
            description="Publications and advisory boards"
        ),
        "data_governance": OntosphereConfig(
            modules=["foundation", "governance"],
            base_ontologies=["bfo2020", "dcat", "prov"],
            description="Data policies and compliance"
        ),
        "minimal": OntosphereConfig(
            modules=["foundation"],
            base_ontologies=["bfo2020"],
            description="Foundation ontology only"
        )
    }
    
    def generate_url(
        self,
        persona: Optional[str] = None,
        custom_config: Optional[OntosphereConfig] = None,
        rdf_url: Optional[str] = None
    ) -> str:
        """Generate Ontosphere startup URL."""
        
        # Select configuration
        if custom_config:
            config = custom_config
        elif persona and persona in self.PERSONAS:
            config = self.PERSONAS[persona]
        else:
            config = self.PERSONAS["knowledge_engineer"]
        
        # Build query parameters
        params = {}
        
        # Add base ontologies (replaces defaults)
        if config.base_ontologies:
            params["ontologies"] = ",".join(config.base_ontologies)
        
        # Add module URLs (in addition to base ontologies)
        if config.modules:
            module_urls = [self.MODULE_URLS[m] for m in config.modules if m in self.MODULE_URLS]
            if module_urls:
                params["ontology"] = ",".join(module_urls)
        
        # Add RDF data URL
        if rdf_url or config.rdf_url:
            params["rdfUrl"] = rdf_url or config.rdf_url
        
        # Load imports control
        if not config.load_imports:
            params["loadImports"] = "false"
        
        # Build URL
        url = self.BASE_URL
        if params:
            url += "?" + urlencode(params, safe=",:/")
        
        return url
    
    def generate_neptune_sparql_url(
        self,
        neptune_endpoint: str,
        modules: Optional[List[str]] = None
    ) -> str:
        """Generate URL to load from Neptune SPARQL endpoint."""
        
        config = OntosphereConfig(
            modules=modules or ["foundation"],
            base_ontologies=["bfo2020"],
            rdf_url=f"{neptune_endpoint}/sparql",
            description="Load from Neptune SPARQL endpoint"
        )
        
        return self.generate_url(custom_config=config)
    
    def generate_local_dev_url(self, local_file_path: str) -> str:
        """Generate URL for local development file."""
        
        config = OntosphereConfig(
            modules=["foundation"],
            base_ontologies=["bfo2020"],
            rdf_url=f"file://{local_file_path}",
            description="Local development file"
        )
        
        return self.generate_url(custom_config=config)
    
    def get_all_persona_urls(self) -> Dict[str, str]:
        """Generate URLs for all personas."""
        return {
            persona: self.generate_url(persona=persona)
            for persona in self.PERSONAS
        }
    
    def get_bookmarklet(self, persona: str = "knowledge_engineer") -> str:
        """Generate bookmarklet JavaScript for quick Ontosphere launch."""
        url = self.generate_url(persona=persona)
        
        js_code = f"javascript:window.open('{url}','ontosphere','width=1400,height=900');"
        
        return js_code
    
    def print_all_configs(self):
        """Print all persona configurations for documentation."""
        print("Ontosphere Configuration URLs\n")
        print("=" * 80)
        
        for persona, config in self.PERSONAS.items():
            url = self.generate_url(persona=persona)
            print(f"\n{persona.upper().replace('_', ' ')}")
            print(f"Description: {config.description}")
            print(f"Modules: {', '.join(config.modules)}")
            print(f"Base Ontologies: {', '.join(config.base_ontologies)}")
            print(f"URL: {url}")
            print("-" * 80)


# CLI usage
if __name__ == "__main__":
    generator = OntosphereConfigGenerator()
    generator.print_all_configs()
