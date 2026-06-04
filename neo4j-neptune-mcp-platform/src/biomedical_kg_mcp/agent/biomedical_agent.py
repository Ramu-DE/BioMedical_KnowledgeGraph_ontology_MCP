"""
BioMedical Knowledge Graph Agent

Strands-based agent with access to all MCP tools for natural language queries.
"""

from typing import Optional, Dict, Any
from .system_prompt import SYSTEM_PROMPT, get_routing_hint


class BioMedicalKGAgent:
    """
    Conversational agent for biomedical knowledge graph queries.
    
    Provides natural language interface to all MCP servers.
    """

    def __init__(self, platform, model_provider: str = "anthropic", model_id: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize agent.
        
        Args:
            platform: MCPPlatform instance with all servers
            model_provider: LLM provider (anthropic, openai, bedrock)
            model_id: Model identifier
        """
        self.platform = platform
        self.model_provider = model_provider
        self.model_id = model_id
        self.conversation_history = []

    async def ask(self, question: str) -> str:
        """
        Ask a question in natural language.
        
        Args:
            question: User question
            
        Returns:
            Answer synthesized from graph queries
        """
        # Provide routing hint
        routing = get_routing_hint(question)
        
        # Build context with system prompt
        context = {
            "system": SYSTEM_PROMPT,
            "question": question,
            "routing_hint": routing,
            "history": self.conversation_history[-5:]  # Last 5 turns
        }
        
        # Execute agent reasoning (simplified - would use Strands SDK)
        response = await self._reason_and_execute(context)
        
        # Store in history
        self.conversation_history.append({
            "question": question,
            "answer": response
        })
        
        return response

    async def ask_with_context(self, question: str, context: Dict[str, Any]) -> str:
        """
        Ask question with additional context.
        
        Args:
            question: User question
            context: Additional context (entities, previous results, etc.)
            
        Returns:
            Answer
        """
        # Add context to question
        enriched = f"{question}\n\nContext: {context}"
        return await self.ask(enriched)

    async def _reason_and_execute(self, context: Dict[str, Any]) -> str:
        """
        Reason about question and execute appropriate tools.
        
        This is a simplified implementation. Full version would use:
        - Strands Agent SDK for agentic reasoning
        - LLM to plan tool sequence
        - Automatic tool selection and chaining
        
        Args:
            context: Question context
            
        Returns:
            Synthesized answer
        """
        question = context["question"]
        question_lower = question.lower()
        
        # Simple keyword-based routing (would be LLM-based in full version)
        
        # Supply/Quality queries → pgGraph
        if "batch" in question_lower or "manufacturing" in question_lower:
            if "trace" in question_lower or "quality" in question_lower:
                # Extract batch/event ID (simplified)
                return "Routing to pgGraph for supply chain traceability...\n" + \
                       "Use: pggraph_trace_quality_event or pggraph_batch_lineage"
        
        # Clinical trial queries → Neo4j
        if "trial" in question_lower or "clinical" in question_lower:
            return "Routing to Neo4j for clinical trial data...\n" + \
                   "Use: neo4j_query with ClinicalTrial label"
        
        # Drug queries → Neo4j
        if "drug" in question_lower and "treat" in question_lower:
            return "Routing to Neo4j for drug-disease relationships...\n" + \
                   "Use: neo4j_query → MATCH (d:Drug)-[:TREATS]->(dis:Disease)"
        
        # Provenance queries → Neptune
        if "provenance" in question_lower or "derived" in question_lower:
            return "Routing to Neptune for provenance tracking...\n" + \
                   "Use: neptune_sparql with PROV-O queries"
        
        # Default response
        return f"""I can help you query the biomedical knowledge graph.

Your question: {question}

Suggested approach:
- Routing: {context.get('routing_hint', 'Neo4j Aura')}
- Available tools: neo4j_query, neptune_sparql, pggraph_*, sync_*

What specific information are you looking for?
1. Entity details (drug, disease, gene)
2. Relationships (what treats what, what causes what)
3. Network analysis (communities, paths)
4. Supply chain traceability
5. Data provenance
"""

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> list:
        """Get conversation history."""
        return self.conversation_history
