"""
Vocabulary Aligner Service

Maps biomedical entities to standardized vocabularies with LLM assistance.
Supports Drug→RxNorm, Disease→ICD-10/SNOMED-CT, AdverseEvent→MedDRA, Gene/Protein→NCIt/UniProt.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .llm_service import LLMService


class VocabMapping(BaseModel):
    """Vocabulary mapping result."""
    source_name: str
    target_vocab: str
    target_code: Optional[str] = None
    target_label: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    method: str  # "llm", "exact_match", "fuzzy"
    needs_review: bool = False


# Vocabulary targets per entity type
VOCAB_TARGETS = {
    "Drug": ["RxNorm"],
    "Disease": ["ICD-10", "SNOMED-CT"],
    "AdverseEvent": ["MedDRA"],
    "Gene": ["NCIt", "UniProt"],
    "Protein": ["NCIt", "UniProt"],
}


class VocabularyAligner:
    """Aligns entities to standard vocabularies with LLM assistance."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.confidence_threshold = 0.7

    async def align(self, entity: str, entity_type: str) -> List[VocabMapping]:
        """
        Align entity to appropriate vocabularies.
        
        Args:
            entity: Entity name to align
            entity_type: Type (Drug, Disease, Gene, etc.)
            
        Returns:
            List of vocabulary mappings with confidence scores
        """
        target_vocabs = VOCAB_TARGETS.get(entity_type, [])
        if not target_vocabs:
            return []

        mappings = []
        for vocab in target_vocabs:
            mapping = await self.suggest_mapping(entity, vocab)
            if mapping:
                mappings.append(mapping)

        return mappings

    async def align_batch(
        self, entities: List[str], entity_type: str
    ) -> List[List[VocabMapping]]:
        """
        Align multiple entities in batch.
        
        Args:
            entities: List of entity names
            entity_type: Entity type
            
        Returns:
            List of mapping lists, one per entity
        """
        results = []
        for entity in entities:
            mappings = await self.align(entity, entity_type)
            results.append(mappings)
        return results

    async def suggest_mapping(
        self, entity_name: str, target_vocab: str
    ) -> Optional[VocabMapping]:
        """
        Suggest vocabulary mapping using LLM.
        
        Args:
            entity_name: Entity to map
            target_vocab: Target vocabulary
            
        Returns:
            VocabMapping with confidence score
        """
        # Try exact match first (rule-based fallback)
        exact_match = self._exact_match(entity_name, target_vocab)
        if exact_match:
            return exact_match

        # Use LLM for intelligent suggestion
        try:
            suggestion = await self.llm_service.suggest_vocab_mapping(
                entity_name, target_vocab
            )
            
            confidence = suggestion.get("confidence", 0.0)
            mapping = VocabMapping(
                source_name=entity_name,
                target_vocab=target_vocab,
                target_code=suggestion.get("code"),
                target_label=suggestion.get("label"),
                confidence=confidence,
                method="llm",
                needs_review=confidence < self.confidence_threshold,
            )
            return mapping

        except Exception:
            # LLM unavailable - return low confidence mapping
            return VocabMapping(
                source_name=entity_name,
                target_vocab=target_vocab,
                confidence=0.0,
                method="llm_failed",
                needs_review=True,
            )

    def _exact_match(
        self, entity_name: str, target_vocab: str
    ) -> Optional[VocabMapping]:
        """
        Rule-based exact string matching (fallback).
        
        Args:
            entity_name: Entity name
            target_vocab: Target vocabulary
            
        Returns:
            VocabMapping if exact match found
        """
        # Simple exact match registry (would be extended with real vocab data)
        exact_matches = {
            "RxNorm": {
                "aspirin": "1191",
                "ibuprofen": "5640",
                "metformin": "6809",
            },
            "ICD-10": {
                "diabetes": "E11",
                "hypertension": "I10",
                "asthma": "J45",
            },
            "SNOMED-CT": {
                "diabetes": "73211009",
                "hypertension": "38341003",
            },
            "MedDRA": {
                "nausea": "10028813",
                "headache": "10019211",
            },
            "NCIt": {
                "BRCA1": "C17965",
                "TP53": "C18438",
            },
        }

        normalized = entity_name.lower().strip()
        vocab_codes = exact_matches.get(target_vocab, {})
        
        if normalized in vocab_codes:
            return VocabMapping(
                source_name=entity_name,
                target_vocab=target_vocab,
                target_code=vocab_codes[normalized],
                target_label=entity_name,
                confidence=1.0,
                method="exact_match",
                needs_review=False,
            )

        return None
