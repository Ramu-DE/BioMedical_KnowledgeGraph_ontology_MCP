"""Property-based tests for IRI Minter service.

Feature: neo4j-neptune-mcp-platform
Property 1: IRI Minting Idempotence
"""

import re

import pytest
from hypothesis import given, strategies as st

from biomedical_kg_mcp.services.iri_minter import IRIMinter


# Hypothesis strategies for generating test data

@st.composite
def entity_properties(draw):
    """Generate random valid entity properties."""
    num_props = draw(st.integers(min_value=1, max_value=10))
    props = {}
    for _ in range(num_props):
        key = draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=20))
        value = draw(st.one_of(
            st.text(min_size=0, max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
        ))
        props[key] = str(value)
    return props


@st.composite
def entity_type_name(draw):
    """Generate valid entity type names."""
    return draw(st.sampled_from([
        "Disease", "Drug", "Gene", "Protein", "Pathway",
        "ClinicalTrial", "Patient", "Biomarker", "Researcher"
    ]))


@pytest.mark.property
class TestIRIMintingIdempotence:
    """Property 1: IRI Minting Idempotence.
    
    For any entity with a set of identifying properties, minting an IRI from
    those properties multiple times SHALL always produce the identical IRI,
    and the IRI SHALL conform to the pattern
    https://biomedkg.org/ontology/{OntologyClass}/{hash}.
    
    Validates: Requirements 3.4, 8.1, 8.2
    """
    
    @given(
        entity_type=entity_type_name(),
        properties=entity_properties(),
    )
    def test_minting_same_properties_produces_identical_iri(self, entity_type, properties):
        """Minting same properties multiple times produces identical IRI."""
        minter = IRIMinter()
        
        # Mint IRI three times with same properties
        iri1 = minter.mint(entity_type, properties)
        iri2 = minter.mint(entity_type, properties)
        iri3 = minter.mint(entity_type, properties)
        
        # All IRIs must be identical
        assert str(iri1) == str(iri2) == str(iri3), \
            "Minting same properties multiple times must produce identical IRI"
    
    @given(
        entity_type=entity_type_name(),
        properties=entity_properties(),
    )
    def test_iri_matches_expected_pattern(self, entity_type, properties):
        """Minted IRI matches pattern https://biomedkg.org/ontology/{Class}/{hash}."""
        minter = IRIMinter()
        
        iri = minter.mint(entity_type, properties)
        iri_string = str(iri)
        
        # Check pattern: base_namespace + entity_type + "/" + 16-char hex hash
        pattern = rf"^https://biomedkg\.org/ontology/{entity_type}/[0-9a-f]{{16}}$"
        assert re.match(pattern, iri_string), \
            f"IRI must match pattern {pattern}, got {iri_string}"
    
    @given(
        entity_type=entity_type_name(),
        properties=entity_properties(),
    )
    def test_reverse_lookup_returns_original_properties(self, entity_type, properties):
        """Reverse lookup returns the original properties."""
        minter = IRIMinter()
        
        iri = minter.mint(entity_type, properties)
        
        # Reverse lookup
        retrieved = minter.reverse_lookup(iri)
        
        assert retrieved is not None, "Reverse lookup must return properties"
        assert retrieved == properties, \
            "Reverse lookup must return original properties"
    
    @given(
        entity_type=entity_type_name(),
        properties=entity_properties(),
    )
    def test_different_property_order_produces_same_iri(self, entity_type, properties):
        """Properties in different order produce the same IRI (canonicalization)."""
        if len(properties) < 2:
            # Skip if less than 2 properties (can't reorder)
            return
        
        minter = IRIMinter()
        
        # Create reversed properties
        reversed_props = {k: v for k, v in reversed(list(properties.items()))}
        
        iri1 = minter.mint(entity_type, properties)
        iri2 = minter.mint(entity_type, reversed_props)
        
        assert str(iri1) == str(iri2), \
            "Property order must not affect IRI (canonicalization)"
    
    @given(
        entity_type=entity_type_name(),
        properties=entity_properties(),
    )
    def test_batch_minting_matches_individual_minting(self, entity_type, properties):
        """Batch minting produces same IRI as individual minting."""
        minter = IRIMinter()
        
        # Individual mint
        iri_individual = minter.mint(entity_type, properties)
        
        # Batch mint
        entities = [{"entity_type": entity_type, "properties": properties}]
        iris_batch = minter.mint_batch(entities)
        
        assert len(iris_batch) == 1
        assert str(iris_batch[0]) == str(iri_individual), \
            "Batch minting must produce same IRI as individual minting"
    
    @given(
        entity_type=entity_type_name(),
        properties1=entity_properties(),
        properties2=entity_properties(),
    )
    def test_different_properties_produce_different_iris(self, entity_type, properties1, properties2):
        """Different properties produce different IRIs (collision resistance)."""
        # Skip if properties are identical
        if properties1 == properties2:
            return
        
        minter = IRIMinter()
        
        iri1 = minter.mint(entity_type, properties1)
        iri2 = minter.mint(entity_type, properties2)
        
        assert str(iri1) != str(iri2), \
            "Different properties must produce different IRIs"
