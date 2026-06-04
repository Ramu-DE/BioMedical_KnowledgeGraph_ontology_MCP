# Ontosphere Integration - Quick Start

## What is Ontosphere?

Ontosphere is a **browser-based RDF knowledge graph editor** that:
- Loads RDF/OWL ontologies visually
- Runs **OWL 2 DL reasoning** (Konclude) in the browser
- Supports **SPARQL queries** and graph layout algorithms
- Exposes **MCP tools** for AI agent integration
- Works entirely client-side (no backend required)

## Why Integrate with Our POC?

Your BioMedical KG platform needs:
1. ✅ **Visual ontology authoring** for 7 OWL modules
2. ✅ **OWL reasoning** before SHACL validation
3. ✅ **SPARQL query** interface for Neptune data
4. ✅ **AI agent integration** via MCP tools

Ontosphere provides all of this, and we've built a bridge to your platform.

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd neo4j-neptune-mcp-platform
pip install -e .
playwright install chromium
```

### 2. Generate Ontology Modules

```bash
python -c "
from src.biomedical_kg_mcp.services.ontology_module_loader import OntologyModuleLoader
loader = OntologyModuleLoader()
loader.load_all_modules()
print('Generated 7 OWL modules in src/biomedical_kg_mcp/ontologies/')
"
```

### 3. Generate Ontosphere URLs

```bash
python -m src.biomedical_kg_mcp.services.ontosphere_config_generator
```

This outputs pre-configured URLs for each persona:
- **Knowledge Engineer**: All 7 modules
- **Clinical Researcher**: Clinical + Patient modules
- **Commercial Analyst**: Commercial + Supply/Quality modules
- **Data Governance**: Governance module

### 4. Open Ontosphere

Copy one of the generated URLs and open in browser:

```
https://thhanke.github.io/ontosphere/?ontologies=bfo2020,foaf&ontology=https://biomedkg.org/ontology/foundation.ttl
```

## Example Workflow

### Scenario: Validate Clinical Trial Ontology

```python
import asyncio
from src.biomedical_kg_mcp.services.ontosphere_client import OntosphereClient
from src.biomedical_kg_mcp.services.ontosphere_validation_bridge import OntosphereValidationBridge
from src.biomedical_kg_mcp.services.shacl_validator import SHACLValidator

async def main():
    # Initialize client
    client = OntosphereClient()
    validator = SHACLValidator()
    
    # Load clinical module
    result = await client.load_ontology(
        "https://biomedkg.org/ontology/clinical.ttl"
    )
    print(f"Loaded: {result.get('triple_count', 0)} triples")
    
    # Add some instance data
    await client.add_node(
        iri="https://biomedkg.org/trial/NCT12345",
        type_iri="https://biomedkg.org/ontology/ClinicalTrial",
        label="Phase 3 Cancer Trial"
    )
    
    await client.add_node(
        iri="https://biomedkg.org/patient/P001",
        type_iri="https://biomedkg.org/ontology/Patient",
        label="Patient 001"
    )
    
    await client.add_link(
        source_iri="https://biomedkg.org/patient/P001",
        target_iri="https://biomedkg.org/trial/NCT12345",
        predicate_iri="https://biomedkg.org/ontology/enrolledIn"
    )
    
    # Run layout
    await client.run_layout("dagre-lr")
    await client.expand_node()  # Show all property cards
    
    # Run OWL reasoning
    reasoning = await client.run_reasoning()
    print(f"Inferred triples: {reasoning.get('inferred_triples', 0)}")
    
    # Export validated RDF
    export = await client.export_graph("turtle")
    print(f"Exported {len(export['data'])} characters of Turtle")
    
    # Clean up
    await client.close()

asyncio.run(main())
```

## MCP Tool Usage

### Via AI Agent (Claude, GPT, etc.)

AI agents can call Ontosphere tools via your MCP platform:

```json
POST /mcp/invoke
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "ontosphere_load_module",
    "arguments": {"module": "clinical"}
  },
  "id": 1
}
```

### Via Python Client

```python
from src.biomedical_kg_mcp.mcp_servers.ontosphere_bridge import OntosphereBridge

bridge = OntosphereBridge()

# Load module
await bridge._load_module("clinical")

# Validate and sync to Neptune
await bridge._sync_to_neptune()
```

## Persona URLs

### Knowledge Engineer (All Modules)
```
https://thhanke.github.io/ontosphere/?ontologies=bfo2020,ro,foaf&ontology=https://biomedkg.org/ontology/foundation.ttl,https://biomedkg.org/ontology/commercial.ttl,https://biomedkg.org/ontology/clinical.ttl,https://biomedkg.org/ontology/medical-affairs.ttl,https://biomedkg.org/ontology/patient.ttl,https://biomedkg.org/ontology/supply-quality.ttl,https://biomedkg.org/ontology/governance.ttl
```

### Clinical Researcher
```
https://thhanke.github.io/ontosphere/?ontologies=bfo2020,foaf&ontology=https://biomedkg.org/ontology/foundation.ttl,https://biomedkg.org/ontology/clinical.ttl,https://biomedkg.org/ontology/patient.ttl
```

### Load from Neptune SPARQL Endpoint
```
https://thhanke.github.io/ontosphere/?rdfUrl=https://your-neptune-cluster.neptune.amazonaws.com:8182/sparql
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Ontosphere Browser                      │
│  • Visual RDF Editor                             │
│  • OWL 2 DL Reasoning (Konclude WASM)           │
│  • SPARQL Query Interface                        │
│  • MCP Tools Exposed                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓ MCP JSON-RPC 2.0
┌──────────────────────────────────────────────────┐
│     Ontosphere MCP Bridge (Your Platform)        │
│  • ontosphere_load_module                        │
│  • ontosphere_validate                           │
│  • ontosphere_sync_to_neptune                    │
└──────────────────┬───────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         ↓                    ↓
┌────────────────┐   ┌────────────────────┐
│ SHACL Validator│   │  Graph Sync Server │
└────────────────┘   └─────────┬──────────┘
                               ↓
                     ┌──────────────────┐
                     │  AWS Neptune     │
                     │  (Production RDF)│
                     └──────────────────┘
```

## Next Steps

1. **Deploy ontology modules** to a public URL (S3, GitHub Pages)
2. **Create SHACL shapes** for all 31 node types
3. **Test full pipeline**: Ontosphere → SHACL → Neptune
4. **Configure vocabulary mappings** (SNOMED-CT, ICD-10, MedDRA)

## Resources

- [Full Integration Guide](./ONTOSPHERE_INTEGRATION.md)
- [Ontosphere GitHub](https://github.com/ThHanke/ontosphere)
- [Ontosphere Live Demo](https://thhanke.github.io/ontosphere/)
- [MCP Specification](https://modelcontextprotocol.io)
