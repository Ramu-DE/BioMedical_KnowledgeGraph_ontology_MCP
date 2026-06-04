"""IRI Minter service for generating stable, deterministic IRIs."""

import hashlib
from typing import Dict, List, Optional
from urllib.parse import quote

from rdflib import URIRef


class IRIMinter:
    """
    IRI Minter generates stable, deterministic Internationalized Resource Identifiers.
    
    IRIs follow the pattern: https://biomedkg.org/ontology/{OntologyClass}/{hash}
    where hash is SHA-256 of canonical properties truncated to 16 characters.
    """
    
    def __init__(self, base_namespace: str = "https://biomedkg.org/ontology/"):
        """
        Initialize IRI Minter.
        
        Args:
            base_namespace: Base IRI namespace
        """
        self.base_namespace = base_namespace
        self._registry: Dict[str, Dict] = {}  # IRI -> properties mapping
    
    def mint(self, entity_type: str, identifying_props: Dict) -> URIRef:
        """
        Mint a stable IRI for an entity.
        
        Args:
            entity_type: Ontology class name (e.g., "Drug", "Disease")
            identifying_props: Dictionary of identifying properties
            
        Returns:
            Minted IRI as URIRef
        """
        # Generate canonical string
        canonical = self._canonicalize(identifying_props)
        
        # Hash and truncate
        hash_value = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]
        
        # Construct IRI
        iri_string = f"{self.base_namespace}{entity_type}/{hash_value}"
        iri = URIRef(iri_string)
        
        # Register for reverse lookup
        self._registry[iri_string] = identifying_props.copy()
        
        return iri
    
    def mint_batch(self, entities: List[Dict]) -> List[URIRef]:
        """
        Mint IRIs for multiple entities.
        
        Args:
            entities: List of dicts with 'entity_type' and 'properties' keys
            
        Returns:
            List of minted IRIs
        """
        return [
            self.mint(entity["entity_type"], entity["properties"])
            for entity in entities
        ]
    
    def reverse_lookup(self, iri: URIRef) -> Optional[Dict]:
        """
        Look up the properties that generated an IRI.
        
        Args:
            iri: IRI to look up
            
        Returns:
            Dictionary of properties, or None if not found
        """
        iri_string = str(iri)
        return self._registry.get(iri_string)
    
    def _canonicalize(self, properties: Dict) -> str:
        """
        Create canonical representation of properties.
        
        Sorts keys alphabetically and joins as key=value pairs with | separator.
        
        Args:
            properties: Dictionary of properties
            
        Returns:
            Canonical string representation
        """
        sorted_items = sorted(properties.items())
        return "|".join(f"{key}={value}" for key, value in sorted_items)
