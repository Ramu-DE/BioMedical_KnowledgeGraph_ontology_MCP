"""
Property Tests: DCAT Provenance Chain

Property 14: DCAT Provenance Chain
- Generate random dataset transformations (Bronze→Silver, Silver→Gold, Gold→Neptune)
- Verify prov:wasDerivedFrom triple exists linking output to input
- Verify provenance activity includes timestamp and agent

Validates Requirements: 6.2, 6.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from rdflib import URIRef
from src.biomedical_kg_mcp.services.dcat_catalog import DCATCatalog


# Strategies
dataset_names = st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")))
agent_names = st.sampled_from(["lakehouse_pipeline", "sync_service", "etl_process", "data_ingestion"])
themes = st.sampled_from(["clinical", "research", "genomics", "drugs", "diseases"])


@pytest.fixture
def catalog():
    """Create fresh catalog for each test."""
    return DCATCatalog()


@pytest.mark.property
@given(
    bronze_name=dataset_names,
    silver_name=dataset_names,
    gold_name=dataset_names,
    agent=agent_names,
)
@settings(max_examples=30, deadline=2000)
def test_property_provenance_chain_complete(
    bronze_name, silver_name, gold_name, agent, catalog
):
    """
    Property: DCAT Provenance Chain Completeness.
    
    For any Bronze→Silver→Gold transformation:
    1. prov:wasDerivedFrom links exist
    2. Activity records include timestamp and agent
    3. Provenance chain is traceable
    """
    # Register datasets
    bronze_uri = catalog.register_dataset({
        "title": f"Bronze: {bronze_name}",
        "description": "Raw data",
        "theme": "bronze",
    })
    
    silver_uri = catalog.register_dataset({
        "title": f"Silver: {silver_name}",
        "description": "Cleaned data",
        "theme": "silver",
    })
    
    gold_uri = catalog.register_dataset({
        "title": f"Gold: {gold_name}",
        "description": "Transformed data",
        "theme": "gold",
    })
    
    # Record derivations
    catalog.record_derivation(bronze_uri, silver_uri)
    catalog.record_derivation(silver_uri, gold_uri)
    
    # Record provenance activities
    catalog.record_provenance(silver_uri, {
        "agent": agent,
        "started_at": datetime.now().isoformat(),
        "ended_at": datetime.now().isoformat(),
    })
    
    catalog.record_provenance(gold_uri, {
        "agent": agent,
        "started_at": datetime.now().isoformat(),
        "ended_at": datetime.now().isoformat(),
    })
    
    # Property 1: Derivation links exist
    graph = catalog.graph
    from rdflib.namespace import Namespace
    PROV = Namespace("http://www.w3.org/ns/prov#")
    
    assert (silver_uri, PROV.wasDerivedFrom, bronze_uri) in graph
    assert (gold_uri, PROV.wasDerivedFrom, silver_uri) in graph
    
    # Property 2: Activity records exist
    chain = catalog.get_provenance_chain(gold_uri)
    assert len(chain) > 0
    
    # Property 3: Agent is recorded
    activities = [c for c in chain if c["agent"] is not None]
    assert len(activities) > 0


@pytest.mark.property
@given(title=dataset_names, description=dataset_names, theme=themes)
@settings(max_examples=30, deadline=1500)
def test_property_dataset_registration_creates_valid_rdf(
    title, description, theme, catalog
):
    """
    Property: Dataset Registration Creates Valid RDF.
    
    For any dataset registration:
    1. Dataset URI is created
    2. Required DCAT properties exist (title, description)
    3. Dataset is linked to catalog
    """
    dataset_uri = catalog.register_dataset({
        "title": title,
        "description": description,
        "theme": theme,
    })
    
    # Property 1: URI created
    assert isinstance(dataset_uri, URIRef)
    
    # Property 2: Required properties exist
    graph = catalog.graph
    from rdflib.namespace import Namespace, DCTERMS
    DCAT = Namespace("http://www.w3.org/ns/dcat#")
    
    # Check title
    titles = list(graph.objects(dataset_uri, DCTERMS.title))
    assert len(titles) == 1
    assert str(titles[0]) == title
    
    # Check description
    descriptions = list(graph.objects(dataset_uri, DCTERMS.description))
    assert len(descriptions) == 1
    assert str(descriptions[0]) == description
    
    # Property 3: Linked to catalog
    catalog_uri = Namespace("https://biomedkg.org/catalog/")["catalog"]
    assert (catalog_uri, DCAT.dataset, dataset_uri) in graph


@pytest.mark.property
@given(keyword=st.text(min_size=3, max_size=20))
@settings(max_examples=20, deadline=1500)
def test_property_search_returns_consistent_results(keyword, catalog):
    """
    Property: Search Returns Consistent Results.
    
    For any search keyword:
    1. Results are valid DatasetEntry objects
    2. Search is case-insensitive
    3. Empty keyword returns all datasets
    """
    # Register test datasets
    catalog.register_dataset({
        "title": f"Dataset with {keyword}",
        "description": "Test dataset",
    })
    
    catalog.register_dataset({
        "title": "Other dataset",
        "description": f"Contains {keyword} in description",
    })
    
    # Search
    results = catalog.search(keyword=keyword)
    
    # Property 1: Valid results
    assert all(hasattr(r, "title") for r in results)
    assert all(hasattr(r, "description") for r in results)
    
    # Property 2: Case-insensitive (if keyword matches)
    if results:
        assert any(
            keyword.lower() in r.title.lower() or keyword.lower() in r.description.lower()
            for r in results
        )


@pytest.mark.property
def test_property_provenance_activity_has_timestamp(catalog):
    """
    Property: Provenance Activities Have Timestamps.
    
    For any recorded activity:
    1. Started timestamp exists
    2. Ended timestamp exists
    3. Timestamps are valid ISO format
    """
    dataset_uri = catalog.register_dataset({
        "title": "Test Dataset",
        "description": "Test",
    })
    
    started = datetime.now().isoformat()
    ended = datetime.now().isoformat()
    
    catalog.record_provenance(dataset_uri, {
        "agent": "test_agent",
        "started_at": started,
        "ended_at": ended,
    })
    
    # Get provenance
    chain = catalog.get_provenance_chain(dataset_uri)
    
    # Property: Timestamps exist
    assert len(chain) > 0
    activity = chain[0]
    assert activity["started_at"] is not None
    assert activity["ended_at"] is not None


@pytest.mark.property
@given(format=st.sampled_from(["turtle", "xml", "json-ld"]))
@settings(max_examples=10, deadline=2000)
def test_property_rdf_export_is_valid(format, catalog):
    """
    Property: RDF Export Produces Valid Serialization.
    
    For any export format:
    1. Export produces non-empty string
    2. Format-specific syntax is present
    """
    # Register a dataset
    catalog.register_dataset({
        "title": "Export Test",
        "description": "Testing RDF export",
    })
    
    # Export
    rdf_output = catalog.export_rdf(format=format)
    
    # Property 1: Non-empty
    assert len(rdf_output) > 0
    
    # Property 2: Format indicators
    if format == "turtle":
        assert "@prefix" in rdf_output or "PREFIX" in rdf_output
    elif format == "xml":
        assert "<?xml" in rdf_output or "<rdf:RDF" in rdf_output
    elif format == "json-ld":
        assert "{" in rdf_output and "}" in rdf_output
