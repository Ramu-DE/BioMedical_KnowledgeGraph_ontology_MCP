# Technology Stack

## Platform Architecture

### MCP (Model Context Protocol)
- **Protocol**: JSON-RPC 2.0 over stdio and SSE transport
- **Purpose**: Enable AI agents to invoke graph database tools
- **Specification**: MCP Server with `tools/list` registration
- **Framework**: Custom Python implementation extending BaseMCPServer

## Graph Databases

### Neo4j Aura DB (Development/Exploration)
- **Version**: Neo4j 5.x
- **Deployment**: Cloud-hosted (Aura)
- **Protocol**: Bolt over TLS (bolt+s://)
- **Driver**: `neo4j>=5.0` Python async driver
- **Graph Model**: Labeled Property Graph (LPG)
- **Query Language**: Cypher
- **Features**:
  - Async connection pooling (max 50 connections)
  - Graph Data Science (GDS) library
  - Path finding algorithms (Dijkstra, BFS)
  - Community detection (Louvain, Label Propagation, WCC)
  - Circuit breaker pattern (5 failures → 30s timeout)
- **Timeout**: 10 seconds per query
- **Auth**: Username/password via environment variables

### AWS Neptune (Production)
- **Version**: Neptune 1.3+
- **Deployment**: AWS managed service
- **Interfaces**:
  - SPARQL 1.1 endpoint (RDF queries)
  - openCypher endpoint (property graph queries)
- **Graph Models**:
  - RDF (Resource Description Framework) with named graphs
  - Labeled Property Graph (via openCypher)
- **Features**:
  - Neptune Streams (change data capture)
  - Bulk loader from S3
  - IAM database authentication
  - Multi-AZ deployment
- **Auth**: AWS IAM SigV4 request signing
- **SDK**: `boto3`, `botocore`, `requests-aws4auth`
- **Retry**: Exponential backoff for HTTP 429 throttling (max 3 retries)

## Data Processing Platform

### Databricks Lakehouse
- **Components**:
  - Databricks Workspace (compute clusters)
  - Delta Lake (ACID storage layer)
  - Spark SQL (distributed processing)
- **SDK**: `databricks-sdk` Python library
- **Auth**: Personal Access Token (PAT)
- **Architecture**: Semantic Medallion (Bronze → Silver → Gold → Graph)
- **Features**:
  - ACID transactions
  - Schema enforcement and evolution
  - Time travel (data versioning)
  - Incremental processing
  - Checkpoint-based recovery

### Delta Lake
- **Version**: Delta Lake 2.x+
- **Storage**: S3-backed Parquet files with transaction log
- **Features**:
  - ACID guarantees
  - Schema validation
  - Time travel queries
  - Merge/upsert operations
  - Audit history

## Semantic Web Technologies

### RDF Stack
- **Library**: `rdflib>=7.0`
- **Serialization Formats**:
  - Turtle (.ttl) - human-readable
  - N-Triples (.nt) - line-oriented for bulk load
  - JSON-LD - JSON-based RDF
  - RDF/XML - legacy XML format
- **Namespaces**:
  - Base: `https://biomedkg.org/ontology/`
  - RDF: `http://www.w3.org/1999/02/22-rdf-syntax-ns#`
  - RDFS: `http://www.w3.org/2000/01/rdf-schema#`
  - OWL: `http://www.w3.org/2002/07/owl#`
  - DCAT: `http://www.w3.org/ns/dcat#`
  - PROV: `http://www.w3.org/ns/prov#`
  - SHACL: `http://www.w3.org/ns/shacl#`

### OWL Ontologies
- **Standard**: OWL 2 (Web Ontology Language)
- **Modules**: 7 domain-specific ontologies
  - Foundation (core biomedical)
  - Commercial (business entities)
  - Clinical (trials, adverse events)
  - Medical Affairs (research papers)
  - Patient (outcomes, demographics)
  - Supply/Quality (manufacturing)
  - Governance (compliance, policies)
- **Storage**: Neptune named graphs
- **Format**: OWL files in Turtle format

### SHACL Validation
- **Library**: `pyshacl`
- **Standard**: W3C SHACL (Shapes Constraint Language)
- **Validation Engine**: Python-native validator
- **Constraint Types**:
  - Cardinality (sh:minCount, sh:maxCount)
  - Datatype (sh:datatype with XSD types)
  - Class membership (sh:class)
  - Value ranges (sh:minInclusive, sh:maxInclusive)
  - Pattern matching (sh:pattern)
  - Controlled vocabularies (sh:in)
- **Report Format**: SHACL Validation Report (Turtle or JSON-LD)
- **Severity Levels**: Violation, Warning, Info

### SPARQL
- **Version**: SPARQL 1.1
- **Features**:
  - SELECT (tabular results)
  - CONSTRUCT (RDF graph results)
  - ASK (boolean results)
  - DESCRIBE (entity description)
  - Named graph queries (GRAPH clause)
  - Property paths
  - Aggregation (COUNT, SUM, AVG)
  - FILTER expressions
- **Result Format**: SPARQL JSON Results

### W3C DCAT & PROV
- **DCAT**: Data Catalog Vocabulary 2.0
  - dcat:Dataset
  - dcat:Distribution
  - dcat:Catalog
  - Temporal and spatial coverage
- **PROV-O**: Provenance Ontology
  - prov:Entity
  - prov:Activity
  - prov:Agent
  - prov:wasDerivedFrom
  - prov:wasGeneratedBy

## AI & Machine Learning

### LLM Integration
- **API**: External LLM service (OpenAI, Anthropic, or custom)
- **Auth**: API key via X-API-Key header
- **Client**: `httpx` async HTTP client
- **Features**:
  - Text embeddings (768-1536 dimensions)
  - Entity resolution (disambiguation)
  - Vocabulary alignment suggestions
  - Schema mapping (CSV → ontology)
  - Retry logic (exponential backoff, max 3)
- **Timeout**: Configurable per operation

### Graph Embeddings
- **Algorithms**:
  - node2vec - Random walk-based structural embeddings
  - TransE - Translational embeddings for knowledge graphs
- **Text Embeddings**:
  - LLM API for node property text
  - Optional: `sentence-transformers` for local embeddings
- **Vector Storage**: Redis or in-memory (numpy arrays)
- **Similarity Search**: Approximate nearest neighbors (ANN)

### Community Detection
- **Algorithms**:
  - Louvain - Modularity optimization
  - Label Propagation - Fast community detection
  - Weakly Connected Components (WCC)
- **Implementation**: Neo4j GDS or NetworkX
- **Output**: Community assignments per node

## Caching & Performance

### Redis
- **Version**: Redis 7.x
- **Client**: `redis[hiredis]` Python library
- **Deployment**: Local or cloud (ElastiCache, Redis Cloud)
- **Features**:
  - Sub-millisecond lookups
  - TTL-based expiration
  - Hash data structures for entity caching
  - String data for query results
- **TTL Configuration**:
  - Query results: 300 seconds (5 minutes)
  - Entity lookups: 3600 seconds (1 hour)
- **Invalidation**: Entity-aware cache invalidation on sync
- **Fallback**: Bypass on Redis unavailability

## Authentication & Security

### AWS IAM
- **Mechanism**: Signature Version 4 (SigV4)
- **Credential Chain**:
  1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  2. EC2 instance profile (IAM role)
  3. Assumed role (STS)
- **SDK**: `botocore.auth.SigV4Auth`
- **Signed Services**: Neptune HTTPS endpoints

### API Key Authentication
- **Method**: X-API-Key HTTP header
- **Storage**: Environment variables or secrets manager
- **Rate Limiting Tiers**:
  - admin: 500 requests/minute
  - ai-agent: 200 requests/minute
  - read-only: 100 requests/minute
  - write: 20 requests/minute

### Neo4j Aura Authentication
- **Method**: Username/password over TLS (bolt+s://)
- **Storage**: Environment variables
- **Variables**:
  - NEO4J_URI (bolt+s://xxx.databases.neo4j.io)
  - NEO4J_USER
  - NEO4J_PASSWORD

## Python Ecosystem

### Core Language
- **Version**: Python 3.11+
- **Features Used**:
  - Async/await (asyncio)
  - Type hints (PEP 484)
  - Dataclasses
  - Context managers
  - Generators

### Key Libraries

#### Data Validation & Configuration
- `pydantic>=2.0` - Data validation with type hints
- `pydantic-settings` - Environment-based configuration
- `python-dotenv` - Load .env files

#### HTTP & Networking
- `httpx` - Async HTTP client
- `requests-aws4auth` - AWS SigV4 signing for requests
- `boto3` - AWS SDK for Python
- `botocore` - Low-level AWS core functionality

#### Graph & RDF
- `neo4j>=5.0` - Neo4j async driver
- `rdflib>=7.0` - RDF manipulation and SPARQL
- `pyshacl` - SHACL validation

#### Data Processing
- `databricks-sdk` - Databricks workspace API
- `pandas` - Tabular data manipulation (optional for CSV processing)
- `numpy` - Numerical arrays for embeddings

#### Caching
- `redis[hiredis]` - Redis client with C parser

#### Testing
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `hypothesis` - Property-based testing
- `moto` - AWS service mocking
- `fakeredis` - In-memory Redis mock

#### Development
- `black` - Code formatting
- `ruff` - Fast Python linter
- `mypy` - Static type checking

## Infrastructure

### AWS Services
- **Neptune** - Graph database
- **S3** - Bulk load staging, RDF export storage
- **IAM** - Authentication and authorization
- **CloudWatch** - Logging and monitoring (optional)
- **Secrets Manager** - Credential storage (optional)

### Deployment Options
- **Local Development**: Docker Compose or Python virtual environment
- **Cloud Development**: AWS Cloud9, EC2 instance
- **Production**: EKS (Kubernetes), ECS (containers), or Lambda functions

## Development Tools

### Version Control
- Git
- GitHub/GitLab for repository hosting

### Dependency Management
- `pyproject.toml` - PEP 518 project metadata
- `poetry` or `pip` - Package installation
- Virtual environments (venv, conda)

### Code Quality
- **Linting**: ruff (replaces flake8, isort)
- **Formatting**: black
- **Type Checking**: mypy with strict mode
- **Testing**: pytest with coverage reporting

### Documentation
- Markdown for documentation
- Docstrings (Google or NumPy style)
- OpenAPI/Swagger for API documentation (optional)

## Data Formats

### Input Formats
- CSV (69 sample files)
- JSON (API responses)
- RDF (Turtle, N-Triples, JSON-LD)

### Output Formats
- JSON (MCP tool responses)
- N-Triples (Neptune bulk load)
- Turtle (SHACL shapes, ontologies)
- SPARQL JSON Results

### Intermediate Formats
- Delta Lake (Parquet + transaction log)
- Redis serialization (JSON strings, msgpack)

## Controlled Vocabularies & Standards

### Biomedical Vocabularies
- **SNOMED-CT** - Systematized Nomenclature of Medicine
- **ICD-10** - International Classification of Diseases, 10th revision
- **MedDRA** - Medical Dictionary for Regulatory Activities
- **LOINC** - Logical Observation Identifiers Names and Codes
- **RxNorm** - Normalized drug names (NLM)
- **NCIt** - National Cancer Institute thesaurus
- **CDISC** - Clinical Data Interchange Standards Consortium
- **BRIDG** - Biomedical Research Integrated Domain Group

### External Standards
- **HL7 FHIR** - Fast Healthcare Interoperability Resources
- **OMOP CDM** - Observational Medical Outcomes Partnership Common Data Model
- **OHDSI** - Observational Health Data Sciences and Informatics
- **ISO IDMP** - Identification of Medicinal Products

## Protocols & Standards

### W3C Standards
- RDF 1.1 (Resource Description Framework)
- RDFS (RDF Schema)
- OWL 2 (Web Ontology Language)
- SPARQL 1.1 (Query language)
- SHACL (Shapes Constraint Language)
- DCAT 2.0 (Data Catalog Vocabulary)
- PROV-O (Provenance Ontology)

### Other Standards
- JSON-RPC 2.0 (MCP protocol)
- OpenAPI 3.x (API specification, optional)
- OAuth 2.0 (future auth enhancement)

## Monitoring & Observability

### Logging
- Python `logging` module
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Metrics (Future)
- Query execution time
- Sync job duration
- Validation error rates
- Cache hit rates
- API request rates

### Tracing (Future)
- OpenTelemetry for distributed tracing
- Span tracking across MCP servers

## Summary by Layer

| Layer | Technologies |
|-------|-------------|
| **AI Agents** | MCP (JSON-RPC 2.0), stdio/SSE transport |
| **MCP Servers** | Python 3.11+, FastAPI, Pydantic |
| **Graph DBs** | Neo4j Aura (Cypher), AWS Neptune (SPARQL/openCypher) |
| **Data Platform** | Databricks, Delta Lake, Spark SQL |
| **Semantic Web** | RDF, OWL, SHACL, SPARQL (rdflib, pyshacl) |
| **AI/ML** | LLM API, node2vec, sentence-transformers |
| **Caching** | Redis 7.x with hiredis |
| **Auth** | AWS IAM SigV4, API keys, Neo4j credentials |
| **Testing** | pytest, hypothesis, moto, fakeredis |
| **Storage** | S3 (N-Triples), Delta Lake (Parquet) |
| **Vocabularies** | SNOMED-CT, ICD-10, MedDRA, LOINC, RxNorm, NCIt |
