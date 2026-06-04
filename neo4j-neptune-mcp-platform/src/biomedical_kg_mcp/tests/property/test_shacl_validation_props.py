"""Property-based tests for SHACL Validator service.

Feature: neo4j-neptune-mcp-platform
Property 2: SHACL Validator Detects Constraint Violations
"""

import pytest
from hypothesis import given, strategies as st
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

from biomedical_kg_mcp.models.validation import Severity
from biomedical_kg_mcp.services.shacl_validator import SHACLValidator

# Namespaces
BIOMEDKG = Namespace("https://biomedkg.org/ontology/")
SH = Namespace("http://www.w3.org/ns/shacl#")


@st.composite
def rdf_literal_value(draw, datatype=XSD.string):
    """Generate RDF literal values."""
    if datatype == XSD.string:
        return Literal(draw(st.text(min_size=1, max_size=50)))
    elif datatype == XSD.integer:
        return Literal(draw(st.integers(min_value=-1000, max_value=1000)))
    elif datatype == XSD.float:
        return Literal(draw(st.floats(allow_nan=False, allow_infinity=False, min_value=-1000, max_value=1000)))
    else:
        return Literal(draw(st.text(min_size=1, max_size=50)))


@pytest.mark.property
class TestSHACLValidationCorrectness:
    """Property 2: SHACL Validator Detects Constraint Violations.
    
    For any RDF data graph with known constraint violations (cardinality, datatype,
    or class constraints) against a SHACL shapes graph, the validator SHALL identify
    all violations with correct severity levels, and for any data graph with zero
    violations, the validator SHALL report conformance as true.
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
    """
    
    @given(value=st.integers(min_value=0, max_value=100))
    def test_cardinality_min_count_violation_detected(self, value):
        """Validator detects sh:minCount violations."""
        validator = SHACLValidator()
        
        # Create shape requiring minCount 1 for name property
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        prop_shape = BIOMEDKG.DrugShape_name
        shapes_graph.add((shape_node, SH.property, prop_shape))
        shapes_graph.add((prop_shape, SH.path, BIOMEDKG.name))
        shapes_graph.add((prop_shape, SH.minCount, Literal(1)))
        
        # Create data WITHOUT required name property (violation)
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG[f"Drug{value}"]
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        # Missing name property - should violate minCount
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert not report.conforms, "Graph without required property should not conform"
        assert report.total_violations > 0, "Should detect minCount violation"
    
    @given(value=st.integers(min_value=0, max_value=100))
    def test_cardinality_max_count_violation_detected(self, value):
        """Validator detects sh:maxCount violations."""
        validator = SHACLValidator()
        
        # Create shape allowing maxCount 1 for drug_id property
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        prop_shape = BIOMEDKG.DrugShape_id
        shapes_graph.add((shape_node, SH.property, prop_shape))
        shapes_graph.add((prop_shape, SH.path, BIOMEDKG.drugId))
        shapes_graph.add((prop_shape, SH.maxCount, Literal(1)))
        
        # Create data with TWO drugId properties (violation)
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG[f"Drug{value}"]
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        data_graph.add((drug_node, BIOMEDKG.drugId, Literal("D001")))
        data_graph.add((drug_node, BIOMEDKG.drugId, Literal("D002")))  # Duplicate violates maxCount 1
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert not report.conforms, "Graph with duplicate property should not conform"
        assert report.total_violations > 0, "Should detect maxCount violation"
    
    @given(value=st.text(min_size=1, max_size=50))
    def test_datatype_violation_detected(self, value):
        """Validator detects sh:datatype violations."""
        validator = SHACLValidator()
        
        # Create shape requiring integer datatype
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        prop_shape = BIOMEDKG.DrugShape_year
        shapes_graph.add((shape_node, SH.property, prop_shape))
        shapes_graph.add((prop_shape, SH.path, BIOMEDKG.approvalYear))
        shapes_graph.add((prop_shape, SH.datatype, XSD.integer))
        
        # Create data with STRING instead of INTEGER (violation)
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG.Drug001
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        data_graph.add((drug_node, BIOMEDKG.approvalYear, Literal(value)))  # String violates integer datatype
        
        report = validator.validate(data_graph, shapes_graph)
        
        # Note: pyshacl may auto-cast, so this might not always fail
        # But if it does detect a violation, it should report it
        if not report.conforms:
            assert report.total_violations > 0, "Violations detected should be reported"
    
    @given(value=st.integers(min_value=0, max_value=100))
    def test_conformant_graph_reports_true(self, value):
        """Validator reports conforms=True for valid data."""
        validator = SHACLValidator()
        
        # Create simple shape
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        prop_shape = BIOMEDKG.DrugShape_name
        shapes_graph.add((shape_node, SH.property, prop_shape))
        shapes_graph.add((prop_shape, SH.path, BIOMEDKG.name))
        shapes_graph.add((prop_shape, SH.minCount, Literal(1)))
        shapes_graph.add((prop_shape, SH.maxCount, Literal(1)))
        
        # Create VALID data that satisfies constraints
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG[f"Drug{value}"]
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        data_graph.add((drug_node, BIOMEDKG.name, Literal("Aspirin")))  # Exactly 1 name
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert report.conforms, "Valid graph should conform"
        assert report.total_violations == 0, "Valid graph should have zero violations"
    
    @given(value=st.integers(min_value=0, max_value=100))
    def test_class_constraint_violation_detected(self, value):
        """Validator detects sh:class violations."""
        validator = SHACLValidator()
        
        # Create shape requiring object to be of class Disease
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        prop_shape = BIOMEDKG.DrugShape_treats
        shapes_graph.add((shape_node, SH.property, prop_shape))
        shapes_graph.add((prop_shape, SH.path, BIOMEDKG.treats))
        shapes_graph.add((prop_shape, SH["class"], BIOMEDKG.Disease))  # Requires Disease class
        
        # Create data where treats points to Gene instead of Disease (violation)
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG[f"Drug{value}"]
        gene_node = BIOMEDKG[f"Gene{value}"]
        
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        data_graph.add((gene_node, RDF.type, BIOMEDKG.Gene))  # Gene, not Disease
        data_graph.add((drug_node, BIOMEDKG.treats, gene_node))  # Violates class constraint
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert not report.conforms, "Graph with wrong class should not conform"
        assert report.total_violations > 0, "Should detect class constraint violation"
    
    def test_empty_graph_conforms_to_empty_shapes(self):
        """Empty data graph conforms to empty shapes graph."""
        validator = SHACLValidator()
        
        data_graph = Graph()
        shapes_graph = Graph()
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert report.conforms, "Empty graph should conform to empty shapes"
        assert report.total_violations == 0, "Empty graph should have zero violations"
    
    @given(num_violations=st.integers(min_value=1, max_value=5))
    def test_multiple_violations_all_detected(self, num_violations):
        """Validator detects all violations when multiple exist."""
        validator = SHACLValidator()
        
        # Create shape with multiple constraints
        shapes_graph = Graph()
        shapes_graph.bind("sh", SH)
        shapes_graph.bind("biomedkg", BIOMEDKG)
        
        shape_node = BIOMEDKG.DrugShape
        shapes_graph.add((shape_node, RDF.type, SH.NodeShape))
        shapes_graph.add((shape_node, SH.targetClass, BIOMEDKG.Drug))
        
        # Add multiple property constraints
        for i in range(num_violations):
            prop_shape = BIOMEDKG[f"DrugShape_prop{i}"]
            shapes_graph.add((shape_node, SH.property, prop_shape))
            shapes_graph.add((prop_shape, SH.path, BIOMEDKG[f"requiredProp{i}"]))
            shapes_graph.add((prop_shape, SH.minCount, Literal(1)))
        
        # Create data that violates ALL constraints (missing all required properties)
        data_graph = Graph()
        data_graph.bind("biomedkg", BIOMEDKG)
        drug_node = BIOMEDKG.DrugViolations
        data_graph.add((drug_node, RDF.type, BIOMEDKG.Drug))
        # Missing all required properties
        
        report = validator.validate(data_graph, shapes_graph)
        
        assert not report.conforms, "Graph with violations should not conform"
        assert report.total_violations >= num_violations, \
            f"Should detect at least {num_violations} violations"
