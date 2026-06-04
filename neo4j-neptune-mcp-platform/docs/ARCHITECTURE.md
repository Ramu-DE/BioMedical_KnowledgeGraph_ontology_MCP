# System Architecture

## High-Level Architecture

The Neo4j-Neptune MCP Platform follows a microservices-oriented architecture with four specialized MCP servers, shared services layer, and multi-tier data processing pipeline.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AI Agents & Clients                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Claude   │  │   GPT    │  │Knowledge │  │   Data   │          │
│  │  Agent   │  │  Agent   │  │ Engineer │  │ Engineer │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
└───────┼─────────────┼─────────────┼─────────────┼────────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │ JSON-RPC 2.0 / MCP
                      │
┌─────────────────────┼───────────────────────────────────────────────┐
│                     ▼   MCP Server Layer                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Neo4j Aura MCP Server                                       │  │
│  │  Tools: neo4j_query, pathfind, community, expand, schema    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Neptune MCP Server                                          │  │
│  │  Tools: sparql, cypher, bulk_load, load_status, status      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Graph Sync Server                                           │  │
│  │  Tools: sync_to_neptune, sync_from_neptune, validate,       │  │
│  │         mint_iris, align_vocabularies, check_status          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Lakehouse MCP Server                                        │  │
│  │  Tools: ingest_bronze, process_silver, transform_gold,      │  │
│  │         run_pipeline, export_to_neptune                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────────┐
│                     ▼   Shared Services Layer                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │   SHACL    │  │    IRI     │  │ Vocabulary │  │    DCAT    │  │
│  │ Validator  │  │   Minter   │  │  Aligner   │  │  Catalog   │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  GraphRAG  │  │  Ontology  │  │   Redis    │  │  Security  │  │
│  │   Engine   │  │  Manager   │  │   Cache    │  │  Service   │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│  ┌────────────┐                                                    │
│  │    LLM     │                                                    │
│  │  Service   │                                                    │
│  └────────────┘                                                    │
└───────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────────┐
│                     ▼   Data Layer                                  │
│  ┌────────────────────────┐      ┌────────────────────────┐        │
│  │   Neo4j Aura DB        │◄────►│    AWS Neptune         │        │
│  │   Cloud LPG            │ Sync │    RDF + openCypher    │        │
│  │   Cypher Queries       │      │    SPARQL Endpoint     │        │
│  └────────────────────────┘      └──────────┬─────────────┘        │
│                                              │                      │
│  ┌────────────────────────┐      ┌──────────▼─────────────┐        │
│  │   Redis Cache          │      │   Neptune Streams      │        │
│  │   Query + Entity       │      │   Change Data Capture  │        │
│  └────────────────────────┘      └────────────────────────┘        │
│                                                                     │
│  ┌────────────────────────┐      ┌────────────────────────┐        │
│  │   AWS S3               │      │   Databricks           │        │
│  │   N-Triples Export     │      │   Delta Lake           │        │
│  │   Bulk Load Staging    │      │   Medallion Layers     │        │
│  └────────────────────────┘      └────────────────────────┘        │
└───────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. MCP Server Layer

#### BaseMCPServer (Abstract Base)

**Responsibilities:**
- JSON-RPC 2.0 protocol handling
- Tool registration via `tools/list` method
- Input validation with JSON Schema
- Error handling and response formatting
- Transport layer abstraction (stdio, SSE)

**Key Methods:**
```python
class BaseMCPServer:
    async def list_tools() -> list[ToolDefinition]
    async def handle_tool_call(tool_name: str, args: dict) -> dict
    async def register_tool(tool: ToolDefinition)
    async def start() -> None
    async def stop() -> None
```

#### Neo4j Aura MCP Server

**Architecture:**
```
┌────────────────────────────────────────┐
│     Neo4j Aura MCP Server              │
│  ┌──────────────────────────────────┐  │
│  │  Tool Router                     │  │
│  │  - neo4j_query                   │  │
│  │  - neo4j_pathfind                │  │
│  │  - neo4j_community               │  │
│  │  - neo4j_expand                  │  │
│  │  - neo4j_schema                  │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  Neo4j Client Service            │  │
│  │  - Connection pooling            │  │
│  │  - Circuit breaker               │  │
│  │  - Query execution               │  │
│  │  - Timeout handling              │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  Cache Interceptor               │  │
│  │  - Check Redis cache             │  │
│  │  - Store results                 │  │
│  └──────────┬───────────────────────┘  │
└─────────────┼─────────────────────────┘
              │
              ▼
      ┌─────────────┐
      │  Neo4j Aura │
      │  bolt+s://  │
      └─────────────┘
```

**Key Components:**
- **Connection Pool**: Max 50 async connections, health checks every 60s
- **Circuit Breaker**: Open after 5 failures, half-open after 30s
- **Timeout Manager**: 10s default, configurable per query
- **Result Transformer**: Convert Neo4j records to JSON-serializable dicts

#### Neptune MCP Server

**Architecture:**
```
┌────────────────────────────────────────┐
│     Neptune MCP Server                 │
│  ┌──────────────────────────────────┐  │
│  │  Tool Router                     │  │
│  │  - neptune_sparql                │  │
│  │  - neptune_cypher                │  │
│  │  - neptune_bulk_load             │  │
│  │  - neptune_load_status           │  │
│  │  - neptune_status                │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  SigV4 Authenticator             │  │
│  │  - AWS credential chain          │  │
│  │  - Request signing               │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  Neptune Client                  │  │
│  │  - SPARQL endpoint               │  │
│  │  - openCypher endpoint           │  │
│  │  - Bulk loader API               │  │
│  │  - Retry with backoff            │  │
│  └──────────┬───────────────────────┘  │
│             │                           │
│  ┌──────────▼───────────────────────┐  │
│  │  Cache Interceptor               │  │
│  └──────────┬───────────────────────┘  │
└─────────────┼─────────────────────────┘
              │
              ▼
      ┌─────────────┐
      │AWS Neptune  │
      │ HTTPS + IAM │
      └─────────────┘
```

**Key Components:**
- **SigV4 Auth**: Boto3 credential provider + botocore signer
- **Dual Interface**: SPARQL (POST to /sparql) + openCypher (POST to /opencypher)
- **Parameterization**: Prepared statements to prevent injection
- **Retry Logic**: Exponential backoff (1s, 2s, 4s) on HTTP 429
- **Bulk Loader**: S3 URI validation, job tracking with polling

#### Graph Sync Server

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│          Graph Sync Server                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Tool Router                                      │  │
│  │  - sync_to_neptune, sync_from_neptune            │  │
│  │  - validate_graph, mint_iris                     │  │
│  │  - align_vocabularies, check_status              │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   │                                      │
│  ┌────────────────▼──────────────────────────────────┐  │
│  │  Sync Orchestrator                               │  │
│  │  - Job queuing                                   │  │
│  │  - Conflict resolution (last-writer-wins)       │  │
│  │  - Audit trail logging                          │  │
│  └─┬──────────┬──────────┬──────────┬──────────────┘  │
│    │          │          │          │                  │
│  ┌─▼────┐  ┌─▼────┐  ┌──▼─────┐  ┌─▼─────────────┐   │
│  │SHACL │  │ IRI  │  │ Vocab  │  │  RDF↔LPG      │   │
│  │Valid │  │Minter│  │Aligner │  │  Converter    │   │
│  └──────┘  └──────┘  └────────┘  └───────────────┘   │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Neptune Streams Consumer                         │ │
│  │  - Read change records                            │ │
│  │  - Maintain checkpoint                            │ │
│  │  - Trigger Neo4j updates                          │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────┐
   │ Neo4j    │        │ Neptune  │
   │ Aura     │        │ + Streams│
   └──────────┘        └──────────┘
```

**Key Components:**
- **Sync Orchestrator**: Async job queue with priority scheduling
- **Bidirectional Converter**: LPG ↔ RDF transformation with property mapping
- **Conflict Resolver**: Timestamp-based with audit trail
- **Stream Consumer**: Checkpoint-based with at-least-once delivery
- **Validation Pipeline**: SHACL → IRI minting → Vocab alignment → Publish

#### Lakehouse MCP Server

**Architecture:**
```
┌──────────────────────────────────────────────────┐
│     Lakehouse MCP Server                         │
│  ┌────────────────────────────────────────────┐  │
│  │  Tool Router                               │  │
│  │  - ingest_bronze, process_silver,          │  │
│  │  - transform_gold, run_pipeline,           │  │
│  │  - export_to_neptune                       │  │
│  └──────────────┬─────────────────────────────┘  │
│                 │                                 │
│  ┌──────────────▼─────────────────────────────┐  │
│  │  Pipeline Orchestrator                     │  │
│  │  - Stage coordination                      │  │
│  │  - Checkpoint recovery                     │  │
│  │  - Incremental processing                  │  │
│  └──┬─────────┬─────────┬─────────────────────┘  │
│     │         │         │                         │
│  ┌──▼───┐ ┌──▼────┐ ┌──▼────┐                   │
│  │Bronze│ │Silver │ │ Gold  │                   │
│  │Stage │ │Stage  │ │Stage  │                   │
│  └──┬───┘ └──┬────┘ └──┬────┘                   │
│     │        │         │                         │
│  ┌──▼────────▼─────────▼─────┐                  │
│  │  Databricks SDK Client    │                  │
│  │  - Workspace API           │                  │
│  │  - Jobs API                │                  │
│  │  - DBFS API                │                  │
│  └────────────────────────────┘                  │
└──────────────────────────────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Databricks    │
    │  Delta Lake    │
    └────────────────┘
```

**Key Components:**
- **Bronze Stage**: CSV ingestion with schema inference, partition by source
- **Silver Stage**: Entity resolution (LLM), IRI minting, deduplication
- **Gold Stage**: Ontology mapping, RDF triple generation, SHACL validation
- **Pipeline Orchestrator**: Databricks jobs with dependencies, checkpoint storage
- **Export Service**: N-Triples serialization to S3 with compression

### 2. Shared Services Layer

#### SHACL Validator Service

**Architecture:**
```
┌────────────────────────────────────┐
│    SHACL Validator                 │
│  ┌──────────────────────────────┐  │
│  │  Shape Loader                │  │
│  │  - Load shapes from disk     │  │
│  │  - Cache in memory           │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  pySHACL Engine              │  │
│  │  - Validate data graph       │  │
│  │  - Generate report           │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Report Processor            │  │
│  │  - Parse validation report   │  │
│  │  - Severity filtering        │  │
│  │  - JSON serialization        │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

**Validation Flow:**
1. Load data graph (rdflib Graph)
2. Resolve applicable shapes by target class
3. Execute pySHACL validation
4. Parse validation report (sh:result, sh:resultSeverity)
5. Return structured ValidationReport with violations

#### IRI Minter Service

**Algorithm:**
```
Input: entity_type (string), properties (dict)

1. Normalize properties:
   - Sort keys alphabetically
   - Convert values to canonical strings
   - Join as "key1=value1|key2=value2|..."

2. Hash:
   - SHA-256(canonical_string)
   - Take first 16 hex characters

3. Mint IRI:
   - Map entity_type to ontology class (e.g., "Drug" → "Drug")
   - Construct: https://biomedkg.org/ontology/{Class}/{hash}

4. Register:
   - Store IRI → properties mapping (reverse lookup)

Output: URIRef IRI
```

**Registry Structure:**
- In-memory dict: `{IRI: canonical_properties}`
- Optional: Persist to Redis for durability

#### Vocabulary Aligner Service

**Architecture:**
```
┌────────────────────────────────────────┐
│    Vocabulary Aligner                  │
│  ┌──────────────────────────────────┐  │
│  │  Rule-Based Matcher              │  │
│  │  - Exact name match              │  │
│  │  - Code lookup (e.g., RxNorm)    │  │
│  │  - Confidence: 1.0               │  │
│  └────────┬─────────────────────────┘  │
│           │                             │
│  ┌────────▼─────────────────────────┐  │
│  │  LLM-Assisted Matcher            │  │
│  │  - Semantic similarity           │  │
│  │  - Context-aware suggestions     │  │
│  │  - Confidence: 0.5 - 0.9         │  │
│  └────────┬─────────────────────────┘  │
│           │                             │
│  ┌────────▼─────────────────────────┐  │
│  │  Vocabulary Resolver             │  │
│  │  - SNOMED-CT, ICD-10, MedDRA     │  │
│  │  - RxNorm, LOINC, NCIt           │  │
│  │  - Return best match + score     │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

**Mapping Flow:**
1. Try exact match on entity name/code
2. If no match, invoke LLM with entity context
3. LLM suggests top-3 candidate codes with explanations
4. Select best match above threshold (0.7)
5. Flag for manual review if below threshold

#### GraphRAG Engine

**Architecture:**
```
┌────────────────────────────────────────┐
│    GraphRAG Engine                     │
│  ┌──────────────────────────────────┐  │
│  │  Embedding Generator             │  │
│  │  - node2vec (structural)         │  │
│  │  - LLM text embeddings           │  │
│  │  - Combined embedding strategy   │  │
│  └────────┬─────────────────────────┘  │
│           │                             │
│  ┌────────▼─────────────────────────┐  │
│  │  Vector Index                    │  │
│  │  - ANN search (FAISS or similar) │  │
│  │  - Redis vector storage          │  │
│  └────────┬─────────────────────────┘  │
│           │                             │
│  ┌────────▼─────────────────────────┐  │
│  │  Community Detector              │  │
│  │  - Louvain algorithm             │  │
│  │  - Summary generation (LLM)      │  │
│  └────────┬─────────────────────────┘  │
│           │                             │
│  ┌────────▼─────────────────────────┐  │
│  │  Subgraph Extractor              │  │
│  │  - K-hop neighborhood            │  │
│  │  - Relevance filtering           │  │
│  │  - Context serialization         │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

**Embedding Strategy:**
- **Structural**: node2vec random walks (128-dim)
- **Textual**: LLM embeddings of node properties (768-dim)
- **Combined**: Concatenate or average both embeddings

### 3. Data Layer Architecture

#### Neptune + Neo4j Sync Pattern

**Sync Modes:**

**Mode 1: Neo4j → Neptune (Publish)**
```
Neo4j (LPG)
    ↓
Extract subgraph (Cypher query)
    ↓
Convert LPG → RDF triples
    ↓
Mint IRIs for nodes
    ↓
SHACL validation
    ↓ (if valid)
Align to vocabularies (LLM)
    ↓
Publish to Neptune named graph
    ↓
Record audit entry
```

**Mode 2: Neptune → Neo4j (Pull)**
```
Neptune (RDF)
    ↓
SPARQL CONSTRUCT query
    ↓
Convert RDF → LPG
    ↓
Map IRIs to Neo4j IDs
    ↓
MERGE nodes and relationships
    ↓
Update Neo4j
    ↓
Record audit entry
```

**Mode 3: Neptune Streams CDC**
```
Neptune Streams
    ↓
Read change record (ADD/REMOVE triple)
    ↓
Check sync rules (filter by named graph)
    ↓
Convert RDF change → LPG change
    ↓
Apply to Neo4j (MERGE or DELETE)
    ↓
Update checkpoint
```

#### Databricks Medallion Architecture

**Bronze Layer:**
- **Storage**: Delta table `bronze.biomedical_kg`
- **Schema**: Raw columns + metadata (source_file, ingestion_timestamp, batch_id)
- **Partitioning**: By source and date
- **Quality**: No schema enforcement, accept all data

**Silver Layer:**
- **Storage**: Delta table `silver.biomedical_kg_entities`
- **Schema**: Normalized with stable IRIs
- **Processing**:
  - Entity resolution (LLM deduplication)
  - IRI minting (deterministic)
  - Data quality checks (null handling, type casting)
  - Merge strategy: Upsert on entity ID
- **Partitioning**: By entity type

**Gold Layer:**
- **Storage**: Delta table `gold.biomedical_kg_triples`
- **Schema**: (subject_iri, predicate_iri, object, object_type, named_graph)
- **Processing**:
  - Map to ontology modules
  - Generate RDF triples
  - SHACL validation
  - Vocabulary alignment
- **Partitioning**: By named graph

**Export to Neptune:**
- Read Gold layer
- Serialize to N-Triples format
- Write to S3: `s3://bucket/neptune-loads/{batch_id}/graph.nt`
- Trigger Neptune bulk load via API
- Poll for completion

### 4. Security Architecture

#### Authentication Flow

**MCP Tool Invocation:**
```
AI Agent
    ↓ (X-API-Key header)
API Key Validator
    ↓ (valid key)
Rate Limiter (check tier limits)
    ↓ (within limits)
MCP Tool Execution
    ↓
    ├─→ Neo4j Aura (username/password over TLS)
    ├─→ Neptune (SigV4 signed request)
    ├─→ Databricks (PAT token)
    └─→ LLM API (API key)
```

**Neptune SigV4 Signing:**
```
1. Get AWS credentials from chain:
   - Environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
   - EC2 Instance Profile
   - Assumed Role (STS)

2. Construct canonical request:
   - HTTP method + endpoint + headers + payload

3. Sign with SigV4:
   - Region: from NEPTUNE_REGION
   - Service: "neptune-db"
   - Add Authorization header

4. Send HTTPS request
```

#### Rate Limiting

**Implementation:**
- Redis-based token bucket algorithm
- Key: `rate_limit:{api_key}`
- Bucket refill rate based on tier
- Sliding window: 60 seconds

**Tiers:**
| Tier | Requests/min | Typical Use |
|------|--------------|-------------|
| admin | 500 | Platform administrators |
| ai-agent | 200 | AI agents (Claude, GPT) |
| read-only | 100 | Read queries only |
| write | 20 | Write operations |

### 5. Data Flow Patterns

#### End-to-End: CSV to Neptune Production

```
1. CSV Upload
   ↓
2. Lakehouse: Ingest to Bronze
   Tool: ingest_bronze(source_path)
   ↓
3. Lakehouse: Process to Silver
   Tool: process_silver(bronze_batch_id)
   - Entity resolution (LLM)
   - IRI minting
   ↓
4. Lakehouse: Transform to Gold
   Tool: transform_gold(silver_batch_id)
   - Ontology mapping
   - RDF generation
   - SHACL validation
   ↓
5. Lakehouse: Export to S3
   Tool: export_to_neptune(gold_batch_id)
   - Serialize N-Triples
   - Write to S3
   ↓
6. Neptune: Bulk Load
   Tool: neptune_bulk_load(s3_uri)
   - Initiate loader job
   - Poll status
   ↓
7. DCAT: Create Catalog Entry
   - Generate dataset metadata
   - Add provenance (PROV-O)
   - Publish to Neptune
```

#### Query with Caching

```
1. AI Agent → MCP Tool (e.g., neo4j_query)
   ↓
2. Check Redis Cache
   Key: SHA-256(query_text + params)
   ↓
   ├─→ Cache Hit: Return cached result
   │
   └─→ Cache Miss:
       ↓
3. Execute Query (Neo4j or Neptune)
   ↓
4. Store Result in Redis
   TTL: 300s (queries) or 3600s (entities)
   ↓
5. Return Result to Agent
```

## Scalability Considerations

### Horizontal Scaling
- **MCP Servers**: Stateless, can run multiple instances behind load balancer
- **Redis**: Redis Cluster for distributed caching
- **Neptune**: Read replicas for query scaling
- **Databricks**: Auto-scaling clusters

### Vertical Scaling
- **Neo4j Aura**: Upgrade to larger instance sizes
- **Neptune**: Increase instance class (r5, r6g)

### Performance Optimizations
- **Query Optimization**: Use indexes on Neo4j and Neptune
- **Batch Processing**: Bulk operations for sync and ingestion
- **Async I/O**: Python asyncio for concurrent requests
- **Connection Pooling**: Reuse database connections

## Disaster Recovery

### Backup Strategy
- **Neo4j Aura**: Automated cloud backups (provider-managed)
- **Neptune**: Automated snapshots (retention: 35 days)
- **Delta Lake**: S3 versioning + time travel
- **Redis**: AOF persistence + snapshots

### Recovery Procedures
- **Neptune**: Restore from snapshot to new cluster
- **Delta Lake**: Time travel to previous version
- **Sync State**: Rebuild from audit trail + checkpoints

## Monitoring & Observability

### Key Metrics
- Query execution time (p50, p95, p99)
- Sync job duration and success rate
- SHACL validation pass/fail rate
- Cache hit ratio
- API request rate per tier
- Error rate by MCP tool

### Logging Strategy
- Structured JSON logs
- Log aggregation (CloudWatch, ELK)
- Correlation IDs across services
- Audit trail for all mutations

## Summary

The architecture balances:
- **Modularity**: Four specialized MCP servers with clear boundaries
- **Semantic Integrity**: SHACL validation, IRI stability, vocabulary alignment
- **Performance**: Redis caching, async I/O, connection pooling
- **Scalability**: Stateless services, distributed caching, cloud-managed databases
- **Reliability**: Circuit breakers, retry logic, audit trails, checkpointing
