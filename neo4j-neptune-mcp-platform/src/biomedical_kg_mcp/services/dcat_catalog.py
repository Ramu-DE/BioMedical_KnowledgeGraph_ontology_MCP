"""
DCAT Catalog Service with PROV-O Provenance

Implements W3C DCAT 2.0 catalog for dataset metadata with PROV-O provenance tracking.
Tracks Bronze→Silver→Gold transformations and data lineage.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, DCTERMS, XSD


# Namespaces
DCAT = Namespace("http://www.w3.org/ns/dcat#")
PROV = Namespace("http://www.w3.org/ns/prov#")
BIOMEDKG = Namespace("https://biomedkg.org/catalog/")


class DatasetEntry(BaseModel):
    """DCAT Dataset entry."""
    uri: str
    title: str
    description: str
    temporal_coverage: Optional[str] = None
    spatial_coverage: Optional[str] = None
    theme: Optional[str] = None
    distribution_url: Optional[str] = None


class DCATCatalog:
    """W3C DCAT 2.0 Catalog with PROV-O provenance."""

    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        self._init_catalog()

    def _bind_namespaces(self):
        """Bind RDF namespaces."""
        self.graph.bind("dcat", DCAT)
        self.graph.bind("prov", PROV)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("biomedkg", BIOMEDKG)

    def _init_catalog(self):
        """Initialize root catalog."""
        catalog_uri = BIOMEDKG["catalog"]
        self.graph.add((catalog_uri, RDF.type, DCAT.Catalog))
        self.graph.add((catalog_uri, DCTERMS.title, Literal("BioMedical KG Catalog")))
        self.graph.add((catalog_uri, DCTERMS.description, 
                       Literal("Catalog of biomedical knowledge graph datasets")))

    def register_dataset(self, metadata: Dict[str, Any]) -> URIRef:
        """
        Register a dataset in the catalog.
        
        Args:
            metadata: Dataset metadata (title, description, temporal, spatial, theme, distribution)
            
        Returns:
            Dataset URI
        """
        dataset_id = metadata.get("id", self._generate_id(metadata["title"]))
        dataset_uri = BIOMEDKG[f"dataset/{dataset_id}"]
        
        # Add dataset to catalog
        catalog_uri = BIOMEDKG["catalog"]
        self.graph.add((catalog_uri, DCAT.dataset, dataset_uri))
        
        # Dataset properties
        self.graph.add((dataset_uri, RDF.type, DCAT.Dataset))
        self.graph.add((dataset_uri, DCTERMS.title, Literal(metadata["title"])))
        self.graph.add((dataset_uri, DCTERMS.description, Literal(metadata["description"])))
        
        # Optional properties
        if metadata.get("temporal_coverage"):
            self.graph.add((dataset_uri, DCTERMS.temporal, Literal(metadata["temporal_coverage"])))
        
        if metadata.get("spatial_coverage"):
            self.graph.add((dataset_uri, DCTERMS.spatial, Literal(metadata["spatial_coverage"])))
        
        if metadata.get("theme"):
            self.graph.add((dataset_uri, DCAT.theme, Literal(metadata["theme"])))
        
        # Distribution
        if metadata.get("distribution_url"):
            dist_uri = URIRef(dataset_uri + "/distribution")
            self.graph.add((dataset_uri, DCAT.distribution, dist_uri))
            self.graph.add((dist_uri, RDF.type, DCAT.Distribution))
            self.graph.add((dist_uri, DCAT.accessURL, URIRef(metadata["distribution_url"])))
        
        return dataset_uri

    def record_provenance(self, dataset_iri: URIRef, activity: Dict[str, Any]) -> None:
        """
        Record PROV-O provenance for dataset activity.
        
        Args:
            dataset_iri: Dataset URI
            activity: Activity metadata (type, agent, started_at, ended_at)
        """
        activity_id = activity.get("id", self._generate_id(f"activity-{datetime.now().isoformat()}"))
        activity_uri = BIOMEDKG[f"activity/{activity_id}"]
        
        # Activity
        self.graph.add((activity_uri, RDF.type, PROV.Activity))
        self.graph.add((activity_uri, PROV.used, dataset_iri))
        
        # Timestamps
        if activity.get("started_at"):
            self.graph.add((activity_uri, PROV.startedAtTime, 
                           Literal(activity["started_at"], datatype=XSD.dateTime)))
        
        if activity.get("ended_at"):
            self.graph.add((activity_uri, PROV.endedAtTime, 
                           Literal(activity["ended_at"], datatype=XSD.dateTime)))
        
        # Agent
        if activity.get("agent"):
            agent_uri = BIOMEDKG[f"agent/{activity['agent']}"]
            self.graph.add((activity_uri, PROV.wasAssociatedWith, agent_uri))
            self.graph.add((agent_uri, RDF.type, PROV.Agent))
            self.graph.add((agent_uri, PROV.label, Literal(activity["agent"])))
        
        # Link dataset to activity
        self.graph.add((dataset_iri, PROV.wasGeneratedBy, activity_uri))

    def record_derivation(self, source_iri: URIRef, derived_iri: URIRef) -> None:
        """
        Record derivation relationship (e.g., Bronze→Silver→Gold).
        
        Args:
            source_iri: Source dataset URI
            derived_iri: Derived dataset URI
        """
        self.graph.add((derived_iri, PROV.wasDerivedFrom, source_iri))

    def search(
        self,
        keyword: Optional[str] = None,
        theme: Optional[str] = None,
        temporal: Optional[str] = None,
    ) -> List[DatasetEntry]:
        """
        Search catalog for datasets.
        
        Args:
            keyword: Search in title/description
            theme: Filter by theme
            temporal: Filter by temporal coverage
            
        Returns:
            List of matching datasets
        """
        query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        
        SELECT ?dataset ?title ?description ?temporal ?spatial ?theme ?distribution
        WHERE {
            ?catalog dcat:dataset ?dataset .
            ?dataset dcterms:title ?title .
            ?dataset dcterms:description ?description .
            OPTIONAL { ?dataset dcterms:temporal ?temporal . }
            OPTIONAL { ?dataset dcterms:spatial ?spatial . }
            OPTIONAL { ?dataset dcat:theme ?theme . }
            OPTIONAL { 
                ?dataset dcat:distribution ?dist .
                ?dist dcat:accessURL ?distribution .
            }
        """
        
        # Add filters
        filters = []
        if keyword:
            filters.append(f'(CONTAINS(LCASE(?title), "{keyword.lower()}") || CONTAINS(LCASE(?description), "{keyword.lower()}"))')
        if theme:
            filters.append(f'(?theme = "{theme}")')
        if temporal:
            filters.append(f'(?temporal = "{temporal}")')
        
        if filters:
            query += "FILTER (" + " && ".join(filters) + ")"
        
        query += "}"
        
        results = self.graph.query(query)
        
        datasets = []
        for row in results:
            datasets.append(DatasetEntry(
                uri=str(row.dataset),
                title=str(row.title),
                description=str(row.description),
                temporal_coverage=str(row.temporal) if row.temporal else None,
                spatial_coverage=str(row.spatial) if row.spatial else None,
                theme=str(row.theme) if row.theme else None,
                distribution_url=str(row.distribution) if row.distribution else None,
            ))
        
        return datasets

    def get_provenance_chain(self, dataset_iri: URIRef) -> List[Dict[str, Any]]:
        """
        Get full provenance chain for a dataset.
        
        Args:
            dataset_iri: Dataset URI
            
        Returns:
            List of provenance records
        """
        query = """
        PREFIX prov: <http://www.w3.org/ns/prov#>
        
        SELECT ?source ?activity ?agent ?started ?ended
        WHERE {
            ?dataset prov:wasDerivedFrom* ?source .
            OPTIONAL {
                ?source prov:wasGeneratedBy ?activity .
                OPTIONAL { ?activity prov:wasAssociatedWith ?agent . }
                OPTIONAL { ?activity prov:startedAtTime ?started . }
                OPTIONAL { ?activity prov:endedAtTime ?ended . }
            }
        }
        """
        
        results = self.graph.query(query, initBindings={"dataset": dataset_iri})
        
        chain = []
        for row in results:
            chain.append({
                "source": str(row.source),
                "activity": str(row.activity) if row.activity else None,
                "agent": str(row.agent) if row.agent else None,
                "started_at": str(row.started) if row.started else None,
                "ended_at": str(row.ended) if row.ended else None,
            })
        
        return chain

    def export_rdf(self, format: str = "turtle") -> str:
        """
        Export catalog as RDF.
        
        Args:
            format: RDF format (turtle, xml, json-ld)
            
        Returns:
            Serialized RDF
        """
        return self.graph.serialize(format=format)

    def _generate_id(self, name: str) -> str:
        """Generate dataset ID from name."""
        import hashlib
        return hashlib.sha256(name.encode()).hexdigest()[:16]
