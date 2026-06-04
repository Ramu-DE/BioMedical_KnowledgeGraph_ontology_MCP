"""LLM Service for embeddings, entity resolution, and vocabulary alignment."""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from biomedical_kg_mcp.config.settings import LLMSettings


class EntityResolution(BaseModel):
    """Entity resolution result."""
    entity_name: str
    canonical_name: str
    confidence: float
    reasoning: str


class VocabSuggestion(BaseModel):
    """Vocabulary mapping suggestion."""
    entity_name: str
    target_vocab: str
    suggested_code: str
    suggested_term: str
    confidence: float
    reasoning: str


class ColumnMapping(BaseModel):
    """CSV column to ontology property mapping."""
    column_name: str
    ontology_property: str
    data_type: str
    transformation: Optional[str] = None
    confidence: float


class LLMService:
    """
    LLM Service provides AI-assisted entity resolution, vocabulary alignment,
    ontology mapping, and embedding generation.
    
    Includes retry logic with exponential backoff (max 3 retries).
    """
    
    def __init__(self, settings: LLMSettings):
        """
        Initialize LLM Service.
        
        Args:
            settings: LLM configuration settings
        """
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout,
            headers={"Authorization": f"Bearer {settings.api_key}"}
        )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        embeddings = await self.generate_embeddings_batch([text])
        return embeddings[0]
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        return await self._retry_request(
            self._make_embedding_request,
            texts
        )
    
    async def resolve_entity(
        self,
        name: str,
        context: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> EntityResolution:
        """
        Resolve entity using LLM to disambiguate similar entities.
        
        Args:
            name: Entity name to resolve
            context: Contextual information
            candidates: List of candidate entities
            
        Returns:
            Entity resolution result
        """
        prompt = self._build_entity_resolution_prompt(name, context, candidates)
        
        response = await self._retry_request(
            self._make_chat_request,
            prompt
        )
        
        return self._parse_entity_resolution(response, name)
    
    async def suggest_vocab_mapping(
        self,
        entity: Dict[str, Any],
        target_vocab: str
    ) -> VocabSuggestion:
        """
        Suggest vocabulary mapping for an entity.
        
        Args:
            entity: Entity data
            target_vocab: Target vocabulary (SNOMED-CT, ICD-10, MedDRA, RxNorm, etc.)
            
        Returns:
            Vocabulary mapping suggestion
        """
        prompt = self._build_vocab_mapping_prompt(entity, target_vocab)
        
        response = await self._retry_request(
            self._make_chat_request,
            prompt
        )
        
        return self._parse_vocab_suggestion(response, entity, target_vocab)
    
    async def map_columns_to_ontology(
        self,
        columns: List[str],
        ontology_module: str
    ) -> List[ColumnMapping]:
        """
        Map CSV columns to ontology properties.
        
        Args:
            columns: List of CSV column names
            ontology_module: Ontology module name
            
        Returns:
            List of column mappings
        """
        prompt = self._build_column_mapping_prompt(columns, ontology_module)
        
        response = await self._retry_request(
            self._make_chat_request,
            prompt
        )
        
        return self._parse_column_mappings(response, columns)
    
    async def _make_embedding_request(self, texts: List[str]) -> List[List[float]]:
        """Make embedding API request."""
        response = await self.client.post(
            "/embeddings",
            json={
                "model": self.settings.model,
                "input": texts,
            }
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
    
    async def _make_chat_request(self, prompt: str) -> str:
        """Make chat completion API request."""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": self.settings.chat_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def _retry_request(self, func, *args, **kwargs):
        """Retry request with exponential backoff."""
        for attempt in range(self.settings.max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                if attempt == self.settings.max_retries - 1:
                    raise
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
    
    def _build_entity_resolution_prompt(
        self,
        name: str,
        context: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for entity resolution."""
        return f"""Resolve the entity '{name}' given this context: {context}

Candidate entities:
{self._format_candidates(candidates)}

Return the canonical name and confidence (0-1)."""
    
    def _build_vocab_mapping_prompt(self, entity: Dict[str, Any], target_vocab: str) -> str:
        """Build prompt for vocabulary mapping."""
        return f"""Map this entity to {target_vocab}:
Entity: {entity}

Return the code, term, and confidence (0-1)."""
    
    def _build_column_mapping_prompt(self, columns: List[str], ontology_module: str) -> str:
        """Build prompt for column mapping."""
        return f"""Map these CSV columns to {ontology_module} ontology properties:
Columns: {', '.join(columns)}

Return property name, data type, and transformation for each."""
    
    def _format_candidates(self, candidates: List[Dict[str, Any]]) -> str:
        """Format candidate list for prompt."""
        return "\n".join(f"- {c}" for c in candidates)
    
    def _parse_entity_resolution(self, response: str, name: str) -> EntityResolution:
        """Parse entity resolution response."""
        # Simplified parsing - in production, use structured output
        return EntityResolution(
            entity_name=name,
            canonical_name=name,
            confidence=0.9,
            reasoning=response
        )
    
    def _parse_vocab_suggestion(
        self,
        response: str,
        entity: Dict[str, Any],
        target_vocab: str
    ) -> VocabSuggestion:
        """Parse vocabulary suggestion response."""
        # Simplified parsing - in production, use structured output
        return VocabSuggestion(
            entity_name=entity.get("name", ""),
            target_vocab=target_vocab,
            suggested_code="",
            suggested_term="",
            confidence=0.8,
            reasoning=response
        )
    
    def _parse_column_mappings(self, response: str, columns: List[str]) -> List[ColumnMapping]:
        """Parse column mapping response."""
        # Simplified parsing - in production, use structured output
        return [
            ColumnMapping(
                column_name=col,
                ontology_property=col.lower().replace(" ", "_"),
                data_type="string",
                confidence=0.85
            )
            for col in columns
        ]
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
