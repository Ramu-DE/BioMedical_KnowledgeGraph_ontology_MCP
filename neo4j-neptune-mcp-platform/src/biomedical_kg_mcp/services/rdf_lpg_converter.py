"""Bidirectional converter between RDF (Neptune) and LPG (Neo4j)."""

from typing import Any, Dict, List, Tuple

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from biomedical_kg_mcp.services.iri_minter import IRIMinter

# Namespaces
BIOMEDKG = Namespace("https://biomedkg.org/ontology/")


class RDFLPGConverter:
    """
    Bidirectional converter between RDF and Labeled Property Graph formats.
    
    - LPG → RDF: Neo4j nodes/relationships to RDF triples
    - RDF → LPG: RDF triples to Neo4j MERGE statements
    """
    
    def __init__(self, iri_minter: IRIMinter):
        """
        Initialize converter.
        
        Args:
            iri_minter: IRI minter for generating URIs
        """
        self.iri_minter = iri_minter
    
    def lpg_to_rdf(self, nodes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Graph:
        """
        Convert LPG (Neo4j) to RDF triples.
        
        Args:
            nodes: List of Neo4j nodes with properties
            relationships: List of Neo4j relationships
            
        Returns:
            RDF Graph with triples
        """
        g = Graph()
        g.bind("biomedkg", BIOMEDKG)
        
        # Track node ID to IRI mapping
        node_iris: Dict[str, URIRef] = {}
        
        # Convert nodes to RDF
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("label", "Entity")
            properties = {k: v for k, v in node.items() if k not in ["id", "label"]}
            
            # Mint IRI
            iri = self.iri_minter.mint(node_type, {"id": node_id, **properties})
            node_iris[node_id] = iri
            
            # Add type triple
            g.add((iri, RDF.type, BIOMEDKG[node_type]))
            
            # Add property triples
            for prop, value in properties.items():
                if isinstance(value, str):
                    g.add((iri, BIOMEDKG[prop], Literal(value)))
                elif isinstance(value, (int, float)):
                    g.add((iri, BIOMEDKG[prop], Literal(value)))
        
        # Convert relationships to RDF
        for rel in relationships:
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")
            rel_type = rel.get("type")
            
            if source_id in node_iris and target_id in node_iris:
                source_iri = node_iris[source_id]
                target_iri = node_iris[target_id]
                
                # Add relationship triple
                g.add((source_iri, BIOMEDKG[rel_type], target_iri))
                
                # Add relationship properties as reified triples (if any)
                rel_props = {k: v for k, v in rel.items() if k not in ["source_id", "target_id", "type"]}
                # Simplified: property handling could be more sophisticated
        
        return g
    
    def rdf_to_lpg(self, rdf_graph: Graph) -> Tuple[List[str], List[str]]:
        """
        Convert RDF triples to Neo4j MERGE statements.
        
        Args:
            rdf_graph: RDF Graph with triples
            
        Returns:
            Tuple of (node_statements, relationship_statements) as Cypher
        """
        node_statements = []
        relationship_statements = []
        
        # Track entities (subjects with rdf:type)
        entities: Dict[str, Dict[str, Any]] = {}
        
        # Extract entities and their types
        for subj, pred, obj in rdf_graph.triples((None, RDF.type, None)):
            entity_id = str(subj)
            entity_type = str(obj).split("/")[-1]
            
            if entity_id not in entities:
                entities[entity_id] = {
                    "iri": entity_id,
                    "type": entity_type,
                    "properties": {}
                }
        
        # Extract properties for each entity
        for entity_id in entities.keys():
            subj = URIRef(entity_id)
            
            for pred, obj in rdf_graph.predicate_objects(subj):
                if pred == RDF.type:
                    continue
                
                prop_name = str(pred).split("/")[-1]
                
                if isinstance(obj, Literal):
                    # Literal value - add as property
                    entities[entity_id]["properties"][prop_name] = obj.value
                elif isinstance(obj, URIRef):
                    # Object property - will become relationship
                    pass
        
        # Generate MERGE statements for nodes
        for entity_id, entity in entities.items():
            props = entity["properties"]
            props["iri"] = entity_id
            
            # Build properties string
            props_str = ", ".join(f"{k}: ${k}" for k in props.keys())
            
            node_stmt = f"""
            MERGE (n:{entity['type']} {{iri: $iri}})
            SET n += {{{props_str}}}
            """
            node_statements.append(node_stmt.strip())
        
        # Generate MERGE statements for relationships
        for subj, pred, obj in rdf_graph.triples((None, None, None)):
            if pred == RDF.type:
                continue
            
            if isinstance(obj, URIRef) and str(obj) in entities:
                # This is a relationship
                source_iri = str(subj)
                target_iri = str(obj)
                rel_type = str(pred).split("/")[-1].upper()
                
                rel_stmt = f"""
                MATCH (source {{iri: '{source_iri}'}}), (target {{iri: '{target_iri}'}})
                MERGE (source)-[r:{rel_type}]->(target)
                """
                relationship_statements.append(rel_stmt.strip())
        
        return node_statements, relationship_statements
    
    def extract_node_from_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract node data from Neo4j record.
        
        Args:
            record: Neo4j query result record
            
        Returns:
            Normalized node dictionary
        """
        # Simplified extraction - would need more sophisticated handling
        return {
            "id": record.get("id", ""),
            "label": record.get("label", "Entity"),
            **{k: v for k, v in record.items() if k not in ["id", "label"]}
        }
