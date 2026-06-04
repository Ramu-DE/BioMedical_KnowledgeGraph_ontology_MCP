"""SHACL Validator service for validating RDF data against SHACL shapes."""

from pathlib import Path
from typing import Optional

import pyshacl
from rdflib import Graph, URIRef

from biomedical_kg_mcp.models.validation import Severity, ValidationReport, ViolationEntry


class SHACLValidator:
    """
    SHACL Validator validates RDF data graphs against SHACL shape constraints.
    
    Supports cardinality (sh:minCount, sh:maxCount), datatype (sh:datatype),
    and class (sh:class) constraints.
    """
    
    def __init__(self, shapes_dir: Optional[str] = None):
        """
        Initialize SHACL Validator.
        
        Args:
            shapes_dir: Directory containing SHACL shape files (Turtle format)
        """
        self.shapes_dir = Path(shapes_dir) if shapes_dir else None
        self._shapes_cache: dict[str, Graph] = {}
    
    def validate(self, data_graph: Graph, shapes_graph: Graph) -> ValidationReport:
        """
        Validate data graph against SHACL shapes.
        
        Args:
            data_graph: RDF data graph to validate
            shapes_graph: SHACL shapes graph
            
        Returns:
            ValidationReport with violations, warnings, and infos
        """
        # Run pyshacl validation
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            inference='rdfs',
            abort_on_first=False,
        )
        
        # Parse results into ValidationReport
        return self._parse_validation_results(conforms, results_graph)
    
    def validate_entity(self, entity_iri: URIRef, data_graph: Graph) -> ValidationReport:
        """
        Validate a single entity in the data graph.
        
        Args:
            entity_iri: IRI of entity to validate
            data_graph: RDF data graph containing the entity
            
        Returns:
            ValidationReport for this entity
        """
        # Extract entity type from data graph
        from rdflib.namespace import RDF
        entity_types = list(data_graph.objects(entity_iri, RDF.type))
        
        if not entity_types:
            return ValidationReport(
                conforms=False,
                violations=[ViolationEntry(
                    focus_node=str(entity_iri),
                    message="Entity has no rdf:type",
                    severity=Severity.VIOLATION
                )]
            )
        
        # Load shapes for entity type
        entity_type = str(entity_types[0]).split('/')[-1]
        shapes_graph = self.get_shapes_for_type(entity_type)
        
        if not shapes_graph:
            return ValidationReport(
                conforms=True,
                violations=[]
            )
        
        return self.validate(data_graph, shapes_graph)
    
    def get_shapes_for_type(self, node_type: str) -> Optional[Graph]:
        """
        Get SHACL shapes for a specific node type.
        
        Args:
            node_type: Node type name (e.g., "Drug", "Disease")
            
        Returns:
            Graph containing SHACL shapes, or None if not found
        """
        # Check cache
        if node_type in self._shapes_cache:
            return self._shapes_cache[node_type]
        
        # Load from file
        if not self.shapes_dir:
            return None
        
        shape_file = self.shapes_dir / f"{node_type.lower()}_shape.ttl"
        if not shape_file.exists():
            return None
        
        return self.load_shapes(str(shape_file))
    
    def load_shapes(self, shapes_path: str) -> Graph:
        """
        Load SHACL shapes from a file.
        
        Args:
            shapes_path: Path to SHACL shapes file (Turtle format)
            
        Returns:
            Graph containing SHACL shapes
        """
        shapes_graph = Graph()
        shapes_graph.parse(shapes_path, format='turtle')
        
        # Cache by filename
        node_type = Path(shapes_path).stem.replace('_shape', '').title()
        self._shapes_cache[node_type] = shapes_graph
        
        return shapes_graph
    
    def _parse_validation_results(self, conforms: bool, results_graph: Graph) -> ValidationReport:
        """
        Parse pyshacl results graph into ValidationReport.
        
        Args:
            conforms: Whether data conforms to shapes
            results_graph: RDF graph with validation results
            
        Returns:
            ValidationReport
        """
        from rdflib.namespace import RDF, Namespace
        
        SH = Namespace("http://www.w3.org/ns/shacl#")
        
        violations = []
        
        # Iterate over validation results
        for result in results_graph.subjects(RDF.type, SH.ValidationResult):
            focus_node = results_graph.value(result, SH.focusNode)
            result_path = results_graph.value(result, SH.resultPath)
            value = results_graph.value(result, SH.value)
            message = results_graph.value(result, SH.resultMessage)
            severity = results_graph.value(result, SH.resultSeverity)
            source_constraint = results_graph.value(result, SH.sourceConstraintComponent)
            source_shape = results_graph.value(result, SH.sourceShape)
            
            # Map SHACL severity to our enum
            severity_level = Severity.VIOLATION
            if severity:
                severity_str = str(severity).split('#')[-1]
                if severity_str == "Warning":
                    severity_level = Severity.WARNING
                elif severity_str == "Info":
                    severity_level = Severity.INFO
            
            violations.append(ViolationEntry(
                focus_node=str(focus_node) if focus_node else "",
                result_path=str(result_path) if result_path else None,
                value=str(value) if value else None,
                message=str(message) if message else "Validation constraint violated",
                severity=severity_level,
                source_constraint=str(source_constraint) if source_constraint else None,
                source_shape=str(source_shape) if source_shape else None,
            ))
        
        return ValidationReport(
            conforms=conforms,
            violations=violations,
        )
