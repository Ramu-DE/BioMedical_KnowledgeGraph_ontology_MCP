"""
Property Tests: Vocabulary Alignment

Property 5: Vocabulary Alignment Targets Correct Vocabulary Per Entity Type
- Generate random entities of different types
- Verify correct vocabulary is targeted per type
- Verify confidence scores in [0.0, 1.0]
- Verify entities below 0.7 are flagged for review

Validates Requirements: 8.3, 8.4, 8.5, 8.6, 8.7
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock
from src.biomedical_kg_mcp.services.vocab_aligner import (
    VocabularyAligner,
    VOCAB_TARGETS,
)
from src.biomedical_kg_mcp.services.llm_service import LLMService


# Strategies
entity_types = st.sampled_from(["Drug", "Disease", "AdverseEvent", "Gene", "Protein"])
entity_names = st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")))
confidence_scores = st.floats(min_value=0.0, max_value=1.0)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    service = AsyncMock(spec=LLMService)
    return service


@pytest.fixture
def vocab_aligner(mock_llm_service):
    """VocabularyAligner with mocked LLM."""
    return VocabularyAligner(mock_llm_service)


@pytest.mark.property
@given(entity_name=entity_names, entity_type=entity_types, confidence=confidence_scores)
@settings(max_examples=50, deadline=2000)
@pytest.mark.asyncio
async def test_property_vocab_targets_correct_vocabulary(
    entity_name, entity_type, confidence, vocab_aligner, mock_llm_service
):
    """
    Property: Vocabulary Alignment Targets Correct Vocabulary Per Entity Type.
    
    For any entity of a given type, verify:
    1. The correct vocabulary is targeted
    2. Confidence scores are in valid range [0.0, 1.0]
    3. Entities with confidence < 0.7 are flagged for review
    """
    # Mock LLM response
    mock_llm_service.suggest_vocab_mapping.return_value = {
        "code": "TEST123",
        "label": entity_name,
        "confidence": confidence,
    }
    
    # Execute alignment
    mappings = await vocab_aligner.align(entity_name, entity_type)
    
    # Property 1: Correct vocabulary targets
    expected_vocabs = VOCAB_TARGETS.get(entity_type, [])
    if expected_vocabs:
        assert len(mappings) == len(expected_vocabs)
        actual_vocabs = {m.target_vocab for m in mappings}
        assert actual_vocabs == set(expected_vocabs)
    
    # Property 2: Confidence scores in valid range
    for mapping in mappings:
        assert 0.0 <= mapping.confidence <= 1.0
    
    # Property 3: Low confidence entities flagged for review
    for mapping in mappings:
        if mapping.confidence < 0.7:
            assert mapping.needs_review is True
        else:
            assert mapping.needs_review is False


@pytest.mark.property
@given(
    entities=st.lists(entity_names, min_size=1, max_size=10),
    entity_type=entity_types,
)
@settings(max_examples=20, deadline=3000)
@pytest.mark.asyncio
async def test_property_batch_alignment_consistency(
    entities, entity_type, vocab_aligner, mock_llm_service
):
    """
    Property: Batch alignment returns results for all entities.
    
    For any list of entities:
    1. Result list length matches input list length
    2. Each entity gets alignment results
    """
    # Mock LLM responses
    mock_llm_service.suggest_vocab_mapping.return_value = {
        "code": "TEST",
        "label": "test",
        "confidence": 0.8,
    }
    
    # Execute batch alignment
    results = await vocab_aligner.align_batch(entities, entity_type)
    
    # Property: Result count matches input count
    assert len(results) == len(entities)
    
    # Property: Each entity has mappings
    for mappings in results:
        assert isinstance(mappings, list)


@pytest.mark.property
@given(confidence=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_property_confidence_threshold_enforcement(
    confidence, vocab_aligner, mock_llm_service
):
    """
    Property: Confidence threshold is correctly enforced.
    
    Entities with confidence < 0.7 MUST be flagged for review.
    """
    mock_llm_service.suggest_vocab_mapping.return_value = {
        "code": "CODE",
        "label": "label",
        "confidence": confidence,
    }
    
    mapping = await vocab_aligner.suggest_mapping("test_entity", "RxNorm")
    
    assert mapping is not None
    assert mapping.confidence == confidence
    
    # Property: Threshold enforcement
    if confidence < 0.7:
        assert mapping.needs_review is True
    else:
        assert mapping.needs_review is False


@pytest.mark.property
@pytest.mark.asyncio
async def test_property_exact_match_returns_high_confidence(vocab_aligner):
    """
    Property: Exact matches return confidence = 1.0.
    
    Known entities in exact match registry should return perfect confidence.
    """
    # Known exact matches from the registry
    exact_matches = [
        ("aspirin", "RxNorm", "1191"),
        ("diabetes", "ICD-10", "E11"),
        ("BRCA1", "NCIt", "C17965"),
    ]
    
    for entity, vocab, expected_code in exact_matches:
        mapping = await vocab_aligner.suggest_mapping(entity, vocab)
        
        assert mapping is not None
        assert mapping.confidence == 1.0
        assert mapping.target_code == expected_code
        assert mapping.method == "exact_match"
        assert mapping.needs_review is False


@pytest.mark.property
@pytest.mark.asyncio
async def test_property_llm_failure_returns_flagged_mapping(
    vocab_aligner, mock_llm_service
):
    """
    Property: LLM failures return low-confidence, flagged mappings.
    
    When LLM service fails, the system should gracefully degrade.
    """
    # Mock LLM failure
    mock_llm_service.suggest_vocab_mapping.side_effect = Exception("LLM unavailable")
    
    mapping = await vocab_aligner.suggest_mapping("unknown_entity", "RxNorm")
    
    assert mapping is not None
    assert mapping.confidence == 0.0
    assert mapping.needs_review is True
    assert mapping.method == "llm_failed"
