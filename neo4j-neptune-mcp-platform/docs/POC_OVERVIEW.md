# POC Overview: Neo4j-Neptune MCP Platform for BioMedical Knowledge Graph

## Executive Summary

An enterprise-grade semantic knowledge graph platform that bridges AI agents, graph databases, and data lakehouses through the Model Context Protocol (MCP). Enables AI agents like Claude/GPT to interact with a BioMedical Knowledge Graph containing 31 node types and 37 relationship types across oncology, genomics, clinical trials, pharmacology, patient outcomes, supply chain, and governance domains.

## POC Objectives

1. **Enable AI agents** to query rich biomedical knowledge graphs via natural language
2. **Bridge development and production** graphs with automated sync and validation
3. **Transform raw data** into semantic RDF aligned with controlled vocabularies
4. **Support GraphRAG** for AI applications grounded in validated biomedical knowledge
5. **Ensure data quality** with SHACL validation and provenance tracking

## Knowledge Graph Scope

### Data Assets
- **31 node types**: Drugs, Diseases, Genes, Proteins, Clinical Trials, Patients, Manufacturing Sites, Compliance Records, Advisory Boards, etc.
- **37 relationship types**: drug_treats_disease, gene_associated_with_disease, trial_investigates_drug, patient_enrolled_in_trial, etc.
- **69 CSV files** with sample data (25 node files, 41 relationship files)

### Seven Ontology Modules
1. **Foundation** - Core biomedical entities (drugs, diseases, genes, proteins, pathways)
2. **Commercial** - Business entities and commercial operations
3. **Clinical** - Clinical trials, adverse events, biomarkers, patient outcomes
4. **Medical Affairs** - Research papers, publications, researchers, institutions
5. **Patient** - Patient demographics, outcomes, reported outcomes
6. **Supply/Quality** - Manufacturing sites, drug batches, quality events
7. **Governance** - Compliance records, data governance policies, regulatory submissions

### Controlled Vocabularies
- **SNOMED-CT** - Systematic nomenclature for diseases and clinical concepts
- **ICD-10** - International classification of diseases
- **MedDRA** - Medical dictionary for regulatory activities (adverse events)
- **LOINC** - Logical observation identifiers for lab/clinical observations
- **RxNorm** - Normalized drug names
- **NCIt** - National Cancer Institute thesaurus
- **CDISC** - Clinical data interchange standards
- **BRIDG** - Biomedical research integrated domain group

## Architecture Components

### 1. Four MCP Servers (AI Agent Tools)

Each server exposes JSON-RPC 2.0 tools that AI agents can invoke:

#### **Neo4j Aura MCP Server** (Cloud Development Graph)
- **Purpose**: Local development and exploration with cloud-hosted LPG
- **Tools**:
  - `neo4j_query` - Execute Cypher queries
  - `neo4j_pathfind` - Find shortest paths between entities (Dijkstra/BFS)
  - `neo4j_community` - Detect communities (Louvain, Label Propagation, WCC)
  - `neo4j_expand` - Expand node neighborhoods by depth
  - `neo4j_schema` - Retrieve graph schema metadata

#### **Neptune MCP Server** (AWS Production Graph)
- **Purpose**: Production queries with RDF semantics and property graph access
- **Tools**:
  - `neptune_sparql` - Execute SPARQL 1.1 queries (RDF interface)
  - `neptune_cypher` - Execute openCypher queries (property graph interface)
  - `neptune_bulk_load` - Initiate bulk loader from S3
  - `neptune_load_status` - Check bulk load job status
  - `neptune_status` - Get cluster health status
- **Auth**: AWS IAM SigV4 request signing

#### **Graph Sync Server** (Bidirectional Synchronization)
- **Purpose**: Sync Neo4j ↔ Neptune with validation and transformation
- **Tools**:
  - `sync_to_neptune` - Validate, transform, and publish to Neptune
  - `sync_from_neptune` - Pull RDF data and convert to LPG
  - `validate_graph` - SHACL validation
  - `mint_iris` - Generate stable IRIs
  - `align_vocabularies` - Map to controlled vocabularies
  - `check_sync_status` - Monitor sync job progress
- **Features**:
  - SHACL validation (pySHACL)
  - IRI minting with deterministic hashing
  - LLM-assisted vocabulary alignment
  - Neptune Streams CDC (change data capture)
  - Conflict resolution (last-writer-wins)

#### **Lakehouse MCP Server** (Databricks Semantic Medallion)
- **Purpose**: Progressive data refinement pipeline
- **Tools**:
  - `ingest_bronze` - Ingest raw data
  - `process_silver` - Entity resolution + IRI minting
  - `transform_gold` - RDF harmonization with ontology
  - `run_pipeline` - Execute full Bronze → Silver → Gold → Graph
  - `export_to_neptune` - Export Gold layer to S3 for Neptune bulk load
- **Layers**:
  - **Bronze**: Raw CSV ingestion with metadata
  - **Silver**: Clean data with stable IRIs and entity resolution
  - **Gold**: RDF triples aligned with ontology modules

### 2. Supporting Services

#### **SHACL Validator**
- Validates RDF data against shape constraints
- Checks cardinality (min/max counts)
- Validates datatypes (XSD types)
- Enforces class constraints (rdf:type)
- Returns validation reports with severity levels (Violation, Warning, Info)

#### **IRI Minter**
- Generates stable, deterministic IRIs
- Pattern: `https://biomedkg.org/ontology/{Class}/{Hash}`
- Hash: SHA-256(canonical properties) truncated to 16 chars
- Idempotent: same input → same IRI

#### **LLM Service**
- Entity resolution (disambiguate similar entities)
- Vocabulary alignment suggestions
- Schema mapping (CSV columns → ontology properties)
- Text embeddings for GraphRAG
- Exponential backoff retry (max 3 retries)

#### **GraphRAG Engine**
- Knowledge graph embeddings (node2vec + LLM)
- Community detection (Louvain algorithm)
- Subgraph extraction for context injection
- Approximate nearest neighbor search

#### **Redis Cache**
- Query result caching (300s TTL for queries, 3600s for entities)
- Entity-aware invalidation on sync
- Fallback to direct query if Redis unavailable

#### **DCAT Catalog**
- W3C Data Catalog Vocabulary (DCAT 2.0)
- PROV-O provenance tracking
- Dataset metadata (title, description, temporal/spatial coverage)
- Derivation relationships (prov:wasDerivedFrom)

#### **Security Service**
- API key validation (X-API-Key header)
- AWS IAM SigV4 authentication for Neptune
- Neo4j Aura credentials (bolt+s:// with user/password)
- Rate limiting per API key tier

## Data Flow

```
┌─────────────────┐
│  Raw CSV Data   │
│  (69 files)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bronze Layer    │ ← Raw ingestion with metadata
│ (Databricks)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Silver Layer    │ ← Entity resolution + IRI minting + LLM
│ (Databricks)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Gold Layer      │ ← RDF triples + ontology alignment
│ (Databricks)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ S3 N-Triples    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│ AWS Neptune     │◄────►│ Neo4j Aura DB   │
│ (Production)    │ Sync │ (Development)   │
│ RDF + openCypher│      │ Cloud LPG       │
└─────────────────┘      └─────────────────┘
         ▲                        ▲
         │                        │
         └────────────────────────┘
              Neptune Streams CDC
```

## Use Cases

### For AI Agents
- "Find all drugs that treat lung cancer with efficacy > 40%"
- "What genes are associated with Alzheimer's disease?"
- "Show clinical trials investigating pembrolizumab with their outcomes"
- "Which proteins are involved in the MAPK signaling pathway?"
- "Find patient cohorts enrolled in trials for monoclonal antibodies"

### For Knowledge Engineers
- Sync validated data from Neo4j dev → Neptune production
- Ensure all data conforms to SHACL shapes before publishing
- Map biomedical entities to standard vocabularies (SNOMED-CT, ICD-10, RxNorm)
- Track conflicts and audit all sync operations
- Maintain ontology modules and shape definitions

### For Data Engineers
- Run semantic medallion pipeline on new datasets
- Track data lineage with DCAT catalog
- Generate embeddings for GraphRAG applications
- Monitor pipeline execution and handle failures
- Export RDF datasets for external consumption

### For Researchers
- Explore drug-disease relationships with path queries
- Identify communities of related genes or proteins
- Find relevant clinical trials by disease indication
- Discover novel connections through graph algorithms
- Access provenance for data quality assessment

## Key Technologies

### Graph Databases
- **Neo4j Aura DB** - Cloud-hosted labeled property graph for development
- **AWS Neptune** - Managed graph database with SPARQL (RDF) and openCypher (LPG) interfaces

### Data Processing
- **Databricks Lakehouse** - Unified analytics platform with Delta Lake
- **Delta Lake** - ACID transactions, schema enforcement, time travel

### Semantic Web
- **RDF** - Resource Description Framework for semantic triples
- **SPARQL 1.1** - Query language for RDF
- **OWL** - Web Ontology Language for ontology modules
- **SHACL** - Shapes Constraint Language for validation
- **pySHACL** - Python SHACL validator
- **rdflib 7.x** - Python RDF library

### AI & ML
- **Model Context Protocol (MCP)** - JSON-RPC 2.0 for AI agent tools
- **LLM API** - Entity resolution, vocabulary alignment, embeddings
- **node2vec** - Graph embedding algorithm
- **Sentence Transformers** - Text embeddings (optional)

### Infrastructure
- **Redis 7.x** - Query and entity caching
- **AWS S3** - Bulk load staging for Neptune
- **AWS IAM** - SigV4 authentication
- **Neptune Streams** - Change data capture

### Development
- **Python 3.11+** - Primary language
- **FastAPI** - MCP server framework
- **Pydantic** - Data validation and settings
- **pytest** - Testing with Hypothesis for property tests
- **asyncio** - Async/await for concurrent operations

## Success Metrics

1. **Query Performance**: < 10s for Neo4j queries, < 5s for cached results
2. **Sync Reliability**: 100% SHACL validation before Neptune publish
3. **IRI Stability**: Idempotent minting across sync operations
4. **Data Quality**: Zero validation violations for production data
5. **Vocabulary Coverage**: > 80% entity mapping to controlled vocabularies
6. **Pipeline Throughput**: Process 10K records through medallion in < 5 minutes
7. **AI Agent Success**: 90% query success rate from natural language

## Implementation Status

Current phase: **Design & Planning Complete**

Next steps:
1. Project setup and configuration
2. Implement shared services (IRI minter, SHACL validator, LLM service)
3. Build Neo4j Aura MCP Server
4. Build Neptune MCP Server with SigV4 auth
5. Implement Graph Sync Server
6. Build Lakehouse MCP Server
7. Integration testing and validation
8. Load sample data and run end-to-end scenarios

Total tasks: 60+ across 15 work packages
