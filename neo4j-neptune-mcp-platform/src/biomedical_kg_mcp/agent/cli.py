"""
BioMedical KG Agent CLI

Interactive command-line interface for the agent.
"""

import asyncio
from biomedical_kg_mcp.platform import MCPPlatform
from biomedical_kg_mcp.agent.biomedical_agent import BioMedicalKGAgent
from biomedical_kg_mcp.config.settings import PlatformSettings


async def main():
    """Run interactive agent CLI."""
    
    print("🧬 BioMedical Knowledge Graph Agent")
    print("=" * 50)
    print("Initializing platform...")
    
    # Initialize platform
    settings = PlatformSettings()
    platform = MCPPlatform(settings)
    
    # Initialize agent
    agent = BioMedicalKGAgent(platform)
    
    print("✓ Platform ready")
    print("✓ Agent initialized")
    print("\nType your questions or commands:")
    print("  /help    - Show available commands")
    print("  /modules - List ontology modules")
    print("  /context - Show current context")
    print("  /clear   - Clear conversation history")
    print("  /exit    - Exit")
    print("=" * 50)
    
    while True:
        try:
            # Get user input
            question = input("\n🔍 You: ").strip()
            
            if not question:
                continue
            
            # Handle commands
            if question.startswith("/"):
                if question == "/exit":
                    print("\n👋 Goodbye!")
                    break
                elif question == "/help":
                    print_help()
                    continue
                elif question == "/modules":
                    print_modules()
                    continue
                elif question == "/context":
                    print_context(agent)
                    continue
                elif question == "/clear":
                    agent.clear_history()
                    print("✓ Conversation history cleared")
                    continue
                else:
                    print(f"Unknown command: {question}")
                    continue
            
            # Ask agent
            print("\n🤖 Agent: Thinking...")
            answer = await agent.ask(question)
            print(f"\n🤖 Agent:\n{answer}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    # Cleanup
    await platform.close()


def print_help():
    """Print help information."""
    print("""
Available Commands:
  /help    - Show this help message
  /modules - List available ontology modules
  /context - Show conversation context
  /clear   - Clear conversation history
  /exit    - Exit the agent

Available Data Sources:
  • Neo4j Aura    - Foundation, Clinical, Patient entities
  • AWS Neptune   - RDF, SPARQL, cross-module reasoning
  • pgGraph       - Supply/Quality supply chain data
  • Graph Sync    - Data synchronization

Example Questions:
  • "Find drugs that treat diabetes"
  • "Show clinical trials for lung cancer"
  • "Trace batch B123 back to manufacturing site"
  • "What genes are associated with BRCA1?"
  • "Show me quality events from site S001"
""")


def print_modules():
    """Print ontology modules."""
    print("""
Ontology Modules (31 Entity Types):

Foundation (12):
  Disease, Drug, Gene, Protein, Pathway, BiologicalProcess,
  MolecularFunction, Anatomy, CellType, Phenotype, Biomarker, Exposure

Clinical (3):
  ClinicalTrial, AdverseEvent, ResearchPaper

Medical Affairs (3):
  AdvisoryBoard, MedicalInformationRequest, Researcher

Patient (3):
  Patient, PatientOutcome, PatientReportedOutcome

Supply/Quality (3):
  ManufacturingSite, DrugBatch, QualityEvent

Commercial (2):
  RegulatorySubmission, ExternalMapping

Governance (2):
  DataGovernancePolicy, ComplianceRecord
""")


def print_context(agent):
    """Print agent context."""
    history = agent.get_history()
    
    if not history:
        print("No conversation history")
        return
    
    print(f"\nConversation History ({len(history)} turns):")
    for i, turn in enumerate(history[-5:], 1):
        print(f"\n{i}. Q: {turn['question'][:80]}...")
        print(f"   A: {turn['answer'][:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
