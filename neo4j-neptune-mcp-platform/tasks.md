# Implementation Plan: Neo4j-Neptune MCP Platform

## Overview

This plan implements a multi-server MCP platform bridging Neo4j Aura DB (cloud LPG) with AWS Neptune (production RDF + openCypher), integrated with Databricks Lakehouse Semantic Medallion architecture, LLM-assisted services, GraphRAG, and Redis caching. The implementation refactors and extends the existing codebase in `src/biomedical_kg_mcp/`.

## Tasks

- [x] 1. Project setup, configuration, and data models
  - [x] 1.1 Refactor configuration module for multi-cloud settings
    - Refactor `src/biomedical_kg_mcp/config/settings.py` to add `Neo4jAuraSettings`, `NeptuneSettings`, `DatabricksSettings`, `LLMSettings`, `RedisSettings` using pydantic-settings `BaseSettings` with `env_prefix`
    - Update `.env.example` with all required environment variables (NEO4J_URI, NEO4J_PASSWORD, NEPTUNE_CLUSTER_ENDPOINT, NEPTUNE_REGION, DATABRICKS_WORKSPACE_URL, DATABRICKS_ACCESS_TOKEN, LLM_API_KEY, REDIS_URL)
    - Add `PlatformSettings` root class that aggregates all sub-settings
    - _Requirements: 1.7, 2.3, 10.1, 10.2_

  - [x] 1.2 Update pyproject.toml with new dependencies
    - Add dependencies: `neo4j>=5.0` (async driver), `boto3`, `botocore`, `requests-aws4auth`, `pyshacl`, `rdflib>=7.0`, `redis[hiredis]`, `hypothesis`, `httpx`, `databricks-sdk`, `numpy`, `sentence-transformers` (optional)
    - Add dev dependencies: `pytest-asyncio`, `pytest-hypothesis`, `moto` (AWS mocking), `fakeredis`
    - _Requirements: 1.1, 2.1, 9.1_

  - [x] 1.3 Define core data models for all 31 node types
    - Refactor `src/biomedical_kg_mcp/models/node_schemas.py` to define Pydantic models for all 31 node types organized by ontology module (Foundation: 12, Commercial: 2, Clinical: 3, Medical Affairs: 3, Patient: 3, Supply/Quality: 3, Governance: 2, GraphRAG: 3, Organizational: 1)
    - Each model must include the ID field, key properties, and ontology source as metadata
    - _Requirements: 5.6, 12.1, 12.2_

  - [x] 1.4 Define relationship schemas for all 37 relationship types
    - Refactor `src/biomedical_kg_mcp/models/relationship_schemas.py` to define all 37 relationship types with source/target node type constraints and optional properties
    - Include `POLICY_GOVERNS_ENTITY` with `enforcement_level` property
    - _Requirements: 5.6, 12.2_

  - [x] 1.5 Create shared base classes for MCP servers
    - Refactor `src/biomedical_kg_mcp/mcp_servers/base.py` to define `BaseMCPServer` with JSON-RPC 2.0 protocol handling, tool registration via `tools/list`, and stdio + SSE transport support
    - Add `ToolDefinition` model with JSON Schema input definitions
    - _Requirements: 1.7, 2.1_

  - [x] 1.6 Define sync, validation, and audit models
    - Refactor `src/biomedical_kg_mcp/models/sync.py` to include `SyncJob`, `ConflictRecord`, `StreamCheckpoint` models
    - Refactor `src/biomedical_kg_mcp/models/validation.py` to include `ValidationReport`, `ViolationEntry` with severity levels
    - Refactor `src/biomedical_kg_mcp/models/audit.py` to include `AuditEntry` with timestamp, tool_name, caller_identity, duration, status fields
    - _Requirements: 3.6, 3.8, 5.1, 10.5_

- [x] 2. Shared services — IRI Minter, SHACL Validator, LLM Service
  - [x] 2.1 Implement IRI Minter service
    - Create `src/biomedical_kg_mcp/services/iri_minter.py` with `IRIMinter` class
    - Implement `mint(entity_type, identifying_props) -> URIRef` using SHA-256 hash of canonical(sorted key=value pairs joined by `|`) truncated to 16 chars
    - Implement `mint_batch(entities) -> list[URIRef]` for bulk minting
    - Implement `reverse_lookup(iri) -> dict | None` using an in-memory registry
    - Base namespace: `https://biomedkg.org/ontology/{OntologyClass}/{hash}`
    - _Requirements: 3.4, 8.1, 8.2_

  - [x]* 2.2 Write property test for IRI minting idempotence
    - **Property 1: IRI Minting Idempotence**
    - Generate random entity properties using Hypothesis; verify minting same props multiple times produces identical IRI; verify IRI matches pattern `https://biomedkg.org/ontology/{Class}/{hash}`
    - **Validates: Requirements 3.4, 8.1, 8.2**

  - [x] 2.3 Implement SHACL Validator service
    - Create `src/biomedical_kg_mcp/services/shacl_validator.py` with `SHACLValidator` class using `pyshacl`
    - Implement `validate(data_graph, shapes_graph) -> ValidationReport` that validates all triples against shape constraints
    - Implement `validate_entity(entity_iri, data_graph) -> ValidationReport` for single entity validation
    - Implement `get_shapes_for_type(node_type) -> Graph` to retrieve applicable shapes
    - Implement `load_shapes(shapes_path)` to load SHACL shape files (Turtle format)
    - Support cardinality (sh:minCount, sh:maxCount), datatype (sh:datatype), and class (sh:class) constraints
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x]* 2.4 Write property test for SHACL validation correctness
    - **Property 2: SHACL Validator Detects Constraint Violations**
    - Generate random RDF data graphs with known violations; verify validator identifies all violations with correct severity; verify conformant graphs report true
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

  - [x] 2.5 Implement LLM Service
    - Create `src/biomedical_kg_mcp/services/llm_service.py` with `LLMService` class
    - Implement `generate_embedding(text) -> list[float]` using configured LLM API endpoint
    - Implement `generate_embeddings_batch(texts) -> list[list[float]]` for bulk embedding
    - Implement `resolve_entity(name, context, candidates) -> EntityResolution` for entity resolution
    - Implement `suggest_vocab_mapping(entity, target_vocab) -> VocabSuggestion` for vocabulary alignment
    - Implement `map_columns_to_ontology(columns, ontology_module) -> list[ColumnMapping]` for schema mapping
    - Add retry logic with exponential backoff (max 3 retries) for API failures
    - _Requirements: 3.5, 7.1, 8.3, 8.4, 8.5, 8.6, 12.3_

  - [x] 2.6 Create SHACL shape definitions for all 20 core node types
    - Create `src/biomedical_kg_mcp/shapes/` directory with Turtle files for each node type
    - Define NodeShapes with sh:targetClass, required properties (sh:minCount 1), datatype constraints, controlled value sets (sh:in)
    - Include shapes for: Disease, Drug, Gene, Protein, Pathway, ClinicalTrial, AdverseEvent, Anatomy, BiologicalProcess, MolecularFunction, Biomarker, CellType, Phenotype, Exposure, ResearchPaper, Researcher, Institution, Entity, Cluster, ClusterSummary
    - _Requirements: 5.6_

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Neo4j Aura MCP Server (5 tools)
  - [x] 4.1 Implement Neo4j Aura client service
    - Refactor `src/biomedical_kg_mcp/services/neo4j_client.py` to use `neo4j` async driver with `bolt+s://` connection to Aura DB
    - Implement connection pooling (max 50 connections), timeout handling (10s default), and health check methods
    - Add circuit breaker pattern (5 failures → open for 30s → half-open with 3 test requests)
    - _Requirements: 1.1, 1.5, 1.6_

  - [x] 4.2 Implement Neo4j Aura MCP Server with 5 tools
    - Create `src/biomedical_kg_mcp/mcp_servers/neo4j_aura_server.py` extending `BaseMCPServer`
    - Implement `neo4j_query` tool: execute Cypher, return structured JSON, enforce 10s timeout
    - Implement `neo4j_pathfind` tool: shortest path with Dijkstra/BFS algorithms, source/target IDs, max_depth
    - Implement `neo4j_community` tool: Louvain/Label Propagation/WCC algorithms with node_labels parameter
    - Implement `neo4j_expand` tool: neighborhood expansion with node_id, depth, rel_types filter
    - Implement `neo4j_schema` tool: return graph schema (node labels, relationship types, property keys)
    - Register all tools via MCP `tools/list` with complete JSON Schema definitions
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x]* 4.3 Write unit tests for Neo4j Aura MCP Server
    - Test each tool with mocked Neo4j driver responses
    - Test timeout handling returns error after 10s
    - Test connection failure returns health status and retry recommendation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 5. Neptune MCP Server (5 tools) with SigV4 auth
  - [x] 5.1 Implement SigV4 authenticator for Neptune
    - Create `src/biomedical_kg_mcp/services/sigv4_auth.py` with `SigV4Authenticator` class
    - Implement request signing using `botocore` SigV4 signer for Neptune HTTP endpoints
    - Support AWS credential chain: environment variables, instance profile, assumed role
    - Sign both SPARQL and openCypher endpoint requests
    - _Requirements: 2.3, 10.2_

  - [x] 5.2 Implement Neptune MCP Server with 5 tools
    - Create `src/biomedical_kg_mcp/mcp_servers/neptune_server.py` extending `BaseMCPServer`
    - Implement `neptune_sparql` tool: execute SPARQL 1.1, return SPARQL JSON Results format, support named_graph parameter
    - Implement `neptune_cypher` tool: execute openCypher against Neptune openCypher endpoint, return structured JSON
    - Implement `neptune_bulk_load` tool: initiate Neptune bulk loader from S3 URI, return job ID
    - Implement `neptune_load_status` tool: query loader status endpoint, return job state + records loaded + errors
    - Implement `neptune_status` tool: return cluster status information
    - Add parameterized query support to prevent injection in both SPARQL and openCypher
    - Add exponential backoff retry (max 3) for HTTP 429 throttling errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x]* 5.3 Write property test for SPARQL injection prevention
    - **Property 18: SPARQL Injection Prevention**
    - Generate parameter values containing SPARQL keywords, quotes, angle brackets, semicolons; verify parameterized queries do not alter query structure
    - **Validates: Requirements 2.8**

  - [x]* 5.4 Write property test for retry with exponential backoff
    - **Property 16: Retry with Exponential Backoff**
    - Simulate HTTP 429 responses; verify retry delays increase exponentially; verify max 3 retries before returning error
    - **Validates: Requirements 2.6**

  - [x]* 5.5 Write unit tests for Neptune MCP Server
    - Test SPARQL query execution with mocked HTTP responses
    - Test openCypher query execution
    - Test bulk load initiation and status checking
    - Test SigV4 signing is applied to all requests
    - Test throttling retry behavior
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

- [x] 6. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Vocabulary Aligner (LLM-assisted)
  - [x] 7.1 Implement Vocabulary Aligner service
    - Create `src/biomedical_kg_mcp/services/vocab_aligner.py` with `VocabularyAligner` class
    - Implement `align(entity, entity_type) -> list[VocabMapping]` that maps entities to correct vocabularies per type (Drug→RxNorm, Disease→ICD-10/SNOMED-CT, AdverseEvent→MedDRA, Gene/Protein→NCIt/UniProt)
    - Implement `align_batch(entities, entity_type) -> list[list[VocabMapping]]` for bulk alignment
    - Implement `suggest_mapping(entity_name, target_vocab) -> VocabMapping` using LLM for intelligent suggestions
    - Return confidence scores [0.0, 1.0]; flag entities with confidence < 0.7 for manual review
    - Add fallback to rule-based alignment (exact string match) when LLM API is unavailable
    - _Requirements: 3.5, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x]* 7.2 Write property test for vocabulary alignment targeting
    - **Property 5: Vocabulary Alignment Targets Correct Vocabulary Per Entity Type**
    - Generate random entities of different types; verify correct vocabulary is targeted per type; verify confidence scores in [0.0, 1.0]; verify entities below 0.7 are flagged
    - **Validates: Requirements 8.3, 8.4, 8.5, 8.6, 8.7**

- [x] 8. Graph Sync MCP Server (6 tools) with SHACL validation + CDC
  - [x] 8.1 Implement LPG ↔ RDF conversion utilities
    - Create `src/biomedical_kg_mcp/services/graph_converter.py` with `GraphConverter` class
    - Implement `lpg_to_rdf(nodes, relationships) -> Graph` converting Neo4j LPG nodes/relationships to RDF triples using ontology mappings
    - Implement `rdf_to_lpg(rdf_graph) -> tuple[list[Node], list[Relationship]]` converting RDF triples back to LPG format
    - Handle all 31 node types and 37 relationship types
    - Preserve all properties during conversion
    - _Requirements: 3.1, 3.2, 11.2, 11.3_

  - [ ]* 8.2 Write property test for CDC conversion correctness
    - **Property 8: Neptune Streams CDC Conversion Correctness**
    - Generate random RDF triples representing entities/relationships; verify RDF→LPG conversion produces valid nodes with all mapped properties preserved; verify checkpoint monotonically increases
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**

  - [x] 8.3 Implement conflict resolution with last-writer-wins
    - Create `src/biomedical_kg_mcp/services/conflict_resolver.py` with `ConflictResolver` class
    - Implement timestamp-based last-writer-wins resolution
    - Record conflict details in audit trail (both previous and new values, source database, timestamps)
    - _Requirements: 3.6_

  - [ ]* 8.4 Write property test for conflict resolution determinism
    - **Property 4: Conflict Resolution is Deterministic (Last-Writer-Wins)**
    - Generate pairs of conflicting entity versions with distinct timestamps; verify the later timestamp always wins regardless of source database
    - **Validates: Requirements 3.6**

  - [x] 8.5 Implement Neptune Streams CDC reader
    - Create `src/biomedical_kg_mcp/services/neptune_streams.py` with `NeptuneStreamReader` class
    - Implement `poll() -> list[StreamRecord]` to read stream records since last checkpoint
    - Implement `process_record(record)` with sync rules: ADD → MERGE into Neo4j, REMOVE → DELETE from Neo4j
    - Implement `save_checkpoint(commit_num)` for persistent checkpoint storage in Redis
    - Implement `handle_retention_gap()` for full resync when checkpoint is behind retention window
    - Configure poll_interval=5s, batch_size=100
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 8.6 Implement Graph Sync MCP Server with 6 tools
    - Create `src/biomedical_kg_mcp/mcp_servers/graph_sync_server.py` extending `BaseMCPServer`
    - Implement `sync_to_neptune` tool: execute Cypher on Aura → IRI mint → vocab align → LPG→RDF → SHACL validate → SPARQL INSERT to Neptune
    - Implement `sync_from_neptune` tool: SPARQL CONSTRUCT from Neptune → RDF→LPG → UNWIND+MERGE into Neo4j Aura
    - Implement `sync_validate` tool: validate subgraph without syncing (dry run)
    - Implement `sync_status` tool: return sync job state
    - Implement `sync_conflicts` tool: list conflicts with since/resolved filters
    - Implement `sync_stream_status` tool: return Neptune Streams checkpoint info
    - Reject entire batch if any entity fails SHACL validation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ]* 8.7 Write property test for sync batch atomicity
    - **Property 3: Sync Batch Atomicity**
    - Generate sync batches with at least one invalid entity; verify entire batch is rejected (no partial writes); verify complete validation report is returned
    - **Validates: Requirements 3.8**

  - [ ]* 8.8 Write unit tests for Graph Sync Server
    - Test sync_to_neptune full pipeline with mocked services
    - Test sync_from_neptune RDF→LPG conversion and Cypher MERGE
    - Test batch rejection on validation failure
    - Test conflict resolution records audit trail
    - Test Neptune Streams checkpoint persistence
    - _Requirements: 3.1, 3.2, 3.6, 3.7, 3.8_

- [ ] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Lakehouse MCP Server (6 tools) with Databricks integration
  - [x] 10.1 Implement Databricks client service
    - Create `src/biomedical_kg_mcp/services/databricks_client.py` with `DatabricksClient` class
    - Connect via `databricks-sdk` using workspace URL + Personal Access Token
    - Implement Delta Lake table operations: read, write, append with ACID transactions
    - Support schema enforcement and time-travel queries
    - _Requirements: 4.6_

  - [x] 10.2 Implement Lakehouse MCP Server with 6 tools
    - Create `src/biomedical_kg_mcp/mcp_servers/lakehouse_server.py` extending `BaseMCPServer`
    - Implement `lakehouse_ingest_bronze` tool: ingest raw data from CSV/API/registry into Bronze Delta Lake table with source metadata and ingestion timestamp
    - Implement `lakehouse_process_silver` tool: apply entity resolution (LLM-assisted), deduplication, IRI minting → Silver Delta Lake table with stable IRIs
    - Implement `lakehouse_transform_gold` tool: map to ontology modules, generate RDF triples, SHACL validate → Gold Delta Lake table
    - Implement `lakehouse_run_pipeline` tool: execute Bronze→Silver→Gold sequentially, return pipeline summary with record counts and timing
    - Implement `lakehouse_export_rdf` tool: export Gold RDF triples to S3 in N-Triples format for Neptune bulk loading
    - Implement `lakehouse_status` tool: return pipeline job status
    - Handle stage failures: record error, mark affected records, allow re-execution of failed stage
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [ ]* 10.3 Write property test for N-Triples export round trip
    - **Property 17: N-Triples Export Round Trip**
    - Generate random RDF graphs from Gold layer; export to N-Triples; parse back; verify isomorphic to original (all triples preserved)
    - **Validates: Requirements 4.7**

  - [ ]* 10.4 Write unit tests for Lakehouse MCP Server
    - Test Bronze ingestion with CSV source including metadata
    - Test Silver processing with entity resolution and IRI minting
    - Test Gold transformation with ontology mapping
    - Test pipeline failure handling and re-execution
    - Test N-Triples export format correctness
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 11. DCAT Catalog with PROV-O
  - [x] 11.1 Implement DCAT Catalog service
    - Refactor `src/biomedical_kg_mcp/services/dcat_catalog.py` to implement full W3C DCAT 2.0 catalog
    - Implement `register_dataset(metadata) -> URIRef` creating DCAT Dataset entries with title, description, distribution, temporal/spatial coverage
    - Implement `record_provenance(dataset_iri, activity)` generating PROV-O triples (prov:Activity, prov:wasAssociatedWith, prov:startedAtTime)
    - Implement `search(keyword, theme, temporal) -> list[DatasetEntry]` for catalog search
    - Implement `record_derivation(source_iri, derived_iri)` creating prov:wasDerivedFrom triples for Bronze→Silver→Gold chains
    - Expose catalog as RDF triples accessible via Neptune SPARQL endpoint
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x]* 11.2 Write property test for DCAT provenance chain
    - **Property 14: DCAT Provenance Chain**
    - Generate random dataset transformations (Bronze→Silver, Silver→Gold, Gold→Neptune); verify prov:wasDerivedFrom triple exists linking output to input; verify provenance activity includes timestamp and agent
    - **Validates: Requirements 6.2, 6.5**

- [x] 12. GraphRAG Engine (embeddings + communities + subgraph extraction)
  - [x] 12.1 Implement GraphRAG Engine service
    - Create `src/biomedical_kg_mcp/services/graphrag_engine.py` with `GraphRAGEngine` class
    - Implement `generate_embeddings(node_ids, method="hybrid") -> EmbeddingResult` combining LLM text embeddings with node2vec structural embeddings
    - Implement `search_similar(query_vector, top_k=10) -> list[SimilarNode]` with approximate nearest neighbor search
    - Implement `detect_communities(algorithm="louvain") -> list[Community]` returning community assignments with LLM-generated summary descriptions
    - Implement `extract_subgraph(seed_id, hops=2, rel_types=None) -> Subgraph` extracting relevant subgraph within hop distance and relationship filter
    - Maintain embedding index updated on Gold layer additions or Neptune graph changes
    - Log affected nodes and return partial results when nodes are disconnected or have insufficient neighborhood
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 12.2 Write property test for embedding similarity ordering
    - **Property 9: Embedding Similarity Ordering**
    - Generate random embedding indexes and query vectors; verify results ordered by descending similarity; verify result count ≤ k; verify consistent dimensionality
    - **Validates: Requirements 7.2**

  - [ ]* 12.3 Write property test for community detection complete assignment
    - **Property 10: Community Detection Complete Assignment**
    - Generate random connected graphs; run community detection; verify every node assigned to exactly one community; verify each community has non-empty summary
    - **Validates: Requirements 7.3**

  - [ ]* 12.4 Write property test for subgraph extraction depth bound
    - **Property 15: Subgraph Extraction Depth Bound**
    - Generate random seed entities and hop distances; extract subgraph; verify all nodes reachable within h hops from seed; verify relationships match type filter
    - **Validates: Requirements 7.4**

- [ ] 13. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Redis caching layer
  - [x] 14.1 Implement Redis cache service
    - Create `src/biomedical_kg_mcp/services/cache_service.py` with `CacheService` class
    - Implement query result caching with key pattern `neo4j:query:{sha256(query+params)}` and `neptune:sparql:{sha256(query)}` (TTL 300s)
    - Implement entity lookup caching with key pattern `entity:{type}:{id}` (TTL 3600s)
    - Implement embedding caching with key pattern `embedding:{node_id}` (TTL 86400s)
    - Implement vocabulary mapping caching with key pattern `vocab:{entity_type}:{name_hash}` (TTL 86400s)
    - Implement entity-aware invalidation: track entity IDs per cache entry, invalidate all entries referencing modified entities on sync
    - Graceful degradation: bypass cache when Redis is unavailable, execute queries directly without error
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 14.2 Write property test for cache correctness
    - **Property 6: Cache Correctness (Store and Retrieve)**
    - Execute queries twice with identical parameters within TTL; verify second returns cached result without DB execution; verify correct TTL applied per cache scope
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 14.3 Write property test for cache invalidation on sync
    - **Property 7: Cache Invalidation on Sync**
    - Create cache entries referencing specific entities; simulate sync modifying some entities; verify affected entries invalidated; verify unaffected entries remain
    - **Validates: Requirements 9.3**

  - [x] 14.4 Integrate cache service with Neo4j Aura and Neptune MCP servers
    - Add cache check before query execution in `neo4j_aura_server.py` (cache hit → return cached result)
    - Add cache check before query execution in `neptune_server.py` (cache hit → return cached result)
    - Add cache store after successful query execution in both servers
    - Wire cache invalidation into Graph Sync Server on sync operations
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 15. Security (API key auth, rate limiting, audit)
  - [x] 15.1 Implement API key authentication middleware
    - Create `src/biomedical_kg_mcp/services/auth_service.py` with `AuthService` class
    - Implement API key validation from `X-API-Key` header
    - Return JSON-RPC 2.0 error with code -32600 on missing/invalid API key
    - Store API keys with associated tier (admin, ai-agent, read-only, write)
    - _Requirements: 10.1, 10.3_

  - [x] 15.2 Implement rate limiting per API key tier
    - Add `RateLimiter` class using Redis-based sliding window counter
    - Configure tier limits: admin=500/min, ai-agent=200/min, read-only=100/min, write=20/min
    - Return JSON-RPC 2.0 error on rate limit exceeded
    - _Requirements: 10.4_

  - [x] 15.3 Implement audit logging service
    - Create `src/biomedical_kg_mcp/services/audit_logger.py` with `AuditLogger` class
    - Log all tool invocations with: timestamp, tool_name, caller_identity, execution_duration, success/failure status
    - Support both successful and failed invocations
    - _Requirements: 10.5_

  - [ ]* 15.4 Write property test for rate limiting enforcement
    - **Property 11: Rate Limiting Enforcement**
    - For each tier, submit N requests within one minute; verify N ≤ limit succeeds; verify N > limit is throttled
    - **Validates: Requirements 10.4**

  - [ ]* 15.5 Write property test for authentication rejection
    - **Property 12: Authentication Rejection**
    - Submit tool invocations without valid API key; verify JSON-RPC error code -32600; verify tool is not executed
    - **Validates: Requirements 10.1, 10.3**

  - [ ]* 15.6 Write property test for audit log completeness
    - **Property 13: Audit Log Completeness**
    - Execute random tool invocations (successful and failed); verify audit log entry exists for each with all required fields
    - **Validates: Requirements 10.5**

- [ ] 16. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16A. pgGraph Integration for Supply/Quality Module (Experimental)
  - [ ] 16A.1 Set up PostgreSQL with pgGraph extension for Supply/Quality schema
    - Create `src/biomedical_kg_mcp/services/pggraph_client.py` with `PgGraphClient` class
    - Define PostgreSQL relational schema for Supply/Quality module:
      - `manufacturing_sites` table (site_id PK, name, country, city, gmp_certified, capacity_units_per_year, last_audit_date)
      - `drug_batches` table (batch_id PK, drug_id FK→drugs, manufacturing_site_id FK→manufacturing_sites, production_date, expiry_date, batch_size, quality_status, release_date)
      - `quality_events` table (event_id PK, batch_id FK→drug_batches, event_type, severity, description, detection_date, resolution_date, capa_id)
      - `drugs` table (drug_id PK, name, drug_type, approval_status) — reference table for FK
    - Create SQL migration scripts in `src/biomedical_kg_mcp/migrations/supply_quality/`
    - Configure pgGraph extension: `CREATE EXTENSION pggraph; SELECT graph.initialize();`
    - pgGraph auto-discovers edges from FK relationships — no manual edge definition needed
    - Add `PostgresSettings` to config with env vars: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    - _Requirements: 3.1 (sync), 12.1 (ontology modules)_

  - [ ] 16A.2 Implement pgGraph query tools for supply chain traceability
    - Add `pggraph_traverse` method: trace from quality_event → batch → drug → manufacturing_site using `graph.traverse(start_node, direction, max_depth)`
    - Add `pggraph_shortest_path` method: find shortest path between any two Supply/Quality entities using `graph.shortest_path(source, target)`
    - Add `pggraph_neighbors` method: get immediate related entities using `graph.neighbors(node_id, edge_type)`
    - Add `pggraph_subgraph` method: extract connected subgraph around a batch/site using `graph.bfs(start, depth)`
    - All queries use plain SQL calling pgGraph functions — no Cypher, no SPARQL
    - _Requirements: 1.2 (path finding), 1.4 (subgraph expansion)_

  - [ ] 16A.3 Implement pgGraph MCP Server tools
    - Create `src/biomedical_kg_mcp/mcp_servers/pggraph_server.py` extending `BaseMCPServer`
    - Implement `pggraph_trace_quality_event` tool: given a quality_event_id, trace back through batch → drug → manufacturing site, returning full chain
    - Implement `pggraph_site_impact` tool: given a manufacturing_site_id, find all batches + quality events + affected drugs (downstream impact analysis)
    - Implement `pggraph_batch_lineage` tool: given a batch_id, return full lineage (site that produced it, drug it's for, any quality events)
    - Implement `pggraph_supply_path` tool: find shortest path between any two Supply/Quality entities
    - Implement `pggraph_query` tool: execute raw SQL with pgGraph graph functions
    - Register all tools via MCP `tools/list` with JSON Schema definitions
    - _Requirements: 1.7 (MCP protocol), 3.1 (sync)_

  - [ ] 16A.4 Implement pgGraph ↔ Neptune sync for Supply/Quality data
    - Create `src/biomedical_kg_mcp/services/pggraph_sync.py` with `PgGraphSyncService` class
    - Implement `sync_to_neptune()`: read Supply/Quality tables via SQL → mint IRIs → convert to RDF triples → SHACL validate → publish to Neptune
    - Implement `sync_from_neptune()`: SPARQL CONSTRUCT Supply/Quality subgraph from Neptune → convert RDF → INSERT/UPDATE into PostgreSQL tables
    - Use the same IRI minting pattern: `https://biomedkg.org/ontology/ManufacturingSite/{hash}`, `https://biomedkg.org/ontology/DrugBatch/{hash}`, `https://biomedkg.org/ontology/QualityEvent/{hash}`
    - Wire into existing Graph Sync Server as an additional sync target
    - _Requirements: 3.1, 3.2, 3.4 (IRI minting)_

  - [ ] 16A.5 Load existing Supply/Quality CSV data into PostgreSQL
    - Create data loader script `scripts/load_pggraph_supply_quality.py`
    - Load `nodes/manufacturing_sites.csv` → `manufacturing_sites` table (10 records)
    - Load `nodes/drug_batches.csv` → `drug_batches` table (20 records)
    - Load `nodes/quality_events.csv` → `quality_events` table (12 records)
    - Load `nodes/drugs.csv` → `drugs` reference table (drug_id, name, drug_type, approval_status only)
    - Verify pgGraph discovers FK edges automatically after data load
    - _Requirements: 4.1 (data ingestion)_

  - [ ]* 16A.6 Write unit tests for pgGraph Supply/Quality tools
    - Test trace_quality_event returns full chain (event → batch → drug + site)
    - Test site_impact returns all downstream entities
    - Test batch_lineage returns complete provenance
    - Test supply_path finds valid shortest path
    - Test sync_to_neptune produces correct RDF triples with proper IRIs
    - Test sync_from_neptune correctly populates PostgreSQL tables
    - Use `testing.postgresql` or Docker PostgreSQL for test isolation

- [x] 17. Integration wiring and deployment

  - [x] 17.1 Implement Ontology Module Manager
    - Create `src/biomedical_kg_mcp/services/ontology_manager.py` with `OntologyManager` class
    - Implement `list_modules()` returning 7 OWL modules (Foundation, Commercial, Clinical, Medical_Affairs, Patient, Supply_Quality, Governance) with namespace URIs and versions
    - Implement `get_class(entity_type)` returning ontology class definition with properties, cardinality, parent classes
    - Implement `map_columns(columns, ontology_module)` returning recommended property mappings using LLM
    - Store ontology modules as OWL files served through Neptune named graph `https://biomedkg.org/ontology/`
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [x] 17.2 Wire all MCP servers into unified platform entry point
    - Create `src/biomedical_kg_mcp/platform.py` as the main platform entry point
    - Initialize all 4 MCP servers (Neo4j Aura, Neptune, Graph Sync, Lakehouse) with shared services
    - Wire auth middleware, rate limiter, and audit logger into request pipeline for all servers
    - Wire cache service into Neo4j Aura and Neptune servers
    - Support both stdio and SSE transport configuration
    - _Requirements: 1.7, 10.1, 10.4, 10.5_

  - [ ] 17.3 Create deployment configuration and Docker Compose
    - Update `docker-compose.yml` to include Redis service (local development)
    - Create `.env.example` with all required environment variables for Neo4j Aura, Neptune, Databricks, LLM API, Redis
    - Create `Dockerfile` for the MCP platform (Python 3.11+ base, install dependencies, expose stdio/SSE)
    - Add health check endpoints for each external service connection
    - _Requirements: 1.6, 2.7, 9.4_

  - [ ] 17.4 Create test configuration and shared fixtures
    - Create `src/biomedical_kg_mcp/tests/conftest.py` with shared fixtures (mock Neo4j driver, mock Neptune HTTP, fakeredis, mock LLM API)
    - Create `src/biomedical_kg_mcp/tests/property/conftest.py` with Hypothesis strategies (entity_properties, rdf_graph, shacl_shapes, cypher_query, sparql_parameter_value)
    - Create directory structure: `tests/property/`, `tests/unit/`, `tests/integration/`
    - Configure pytest markers: `@pytest.mark.property`, `@pytest.mark.integration`
    - _Requirements: All_

  - [ ]* 17.5 Write integration tests for end-to-end flows
    - Test full sync_to_neptune flow: Cypher query → IRI mint → vocab align → validate → publish
    - Test full pipeline flow: Bronze ingest → Silver process → Gold transform → Export
    - Test CDC flow: Neptune stream record → RDF→LPG → Neo4j MERGE
    - Use mocked external services (moto for AWS, fakeredis, mock Neo4j)
    - _Requirements: 3.1, 4.4, 11.1_

- [ ] 18. Strands Agent Layer — Agentic Workflow with MCP Tool Routing
  - [ ] 18.1 Set up Strands Agents SDK and MCP client connections
    - Add `strands-agents` and `strands-agents-tools` to pyproject.toml dependencies
    - Create `src/biomedical_kg_mcp/agent/` package
    - Create `src/biomedical_kg_mcp/agent/mcp_connections.py` defining MCP client connections to all servers:
      - Neo4j Aura MCP Server (stdio transport)
      - Neptune MCP Server (stdio transport)
      - pgGraph MCP Server (stdio transport)
      - Graph Sync MCP Server (stdio transport)
      - Lakehouse MCP Server (stdio transport)
    - Configure MCP clients with proper command paths to each server module
    - Add `STRANDS_MODEL_PROVIDER` and `STRANDS_MODEL_ID` to config settings (default: Bedrock Claude or OpenAI)
    - _Requirements: 1.7, 2.1_

  - [ ] 18.2 Implement ontology-aware system prompt and routing logic
    - Create `src/biomedical_kg_mcp/agent/system_prompt.py` with the agent's system prompt defining:
      - The 7 ontology modules and what data each covers
      - Routing rules: Foundation/Clinical → Neo4j Aura, Supply/Quality → pgGraph, Cross-module/RDF reasoning → Neptune, Data pipeline → Lakehouse
      - Available MCP tools per server and when to use each
      - Instructions for multi-step reasoning (e.g., "find drug in Neo4j, then check its quality events in pgGraph")
    - Create `src/biomedical_kg_mcp/agent/ontology_router.py` with helper logic to detect which ontology module(s) a user question maps to based on keywords and entity types
    - _Requirements: 12.1, 12.2_

  - [ ] 18.3 Implement the main Strands Agent with multi-server MCP tools
    - Create `src/biomedical_kg_mcp/agent/biomedical_agent.py` with `BioMedicalKGAgent` class
    - Initialize Strands `Agent` with:
      - System prompt from 18.2
      - All MCP server connections as tools
      - Model configuration (Bedrock/OpenAI via LLM settings)
    - Implement `ask(question: str) -> str` method that invokes the agent
    - Implement `ask_with_context(question: str, context: dict) -> str` for follow-up questions with session context
    - Agent auto-selects which MCP tools to call based on the question
    - _Requirements: 1.1, 2.1, 7.4_

  - [ ] 18.4 Implement multi-agent coordination for complex queries
    - Create `src/biomedical_kg_mcp/agent/specialists/` with domain specialist agents:
      - `clinical_agent.py` — specialist for Clinical ontology queries (diseases, trials, AEs)
      - `supply_agent.py` — specialist for Supply/Quality queries (batches, sites, quality events)
      - `research_agent.py` — specialist for Medical Affairs queries (papers, researchers, advisory boards)
    - Create `src/biomedical_kg_mcp/agent/orchestrator.py` with orchestrator agent that:
      - Receives user question
      - Determines if single-domain or cross-domain
      - For single-domain: routes to specialist agent
      - For cross-domain: coordinates multiple specialists and merges answers
    - _Requirements: 7.3, 7.4, 12.1_

  - [ ] 18.5 Implement conversational memory and session management
    - Create `src/biomedical_kg_mcp/agent/memory.py` with session state management
    - Implement conversation history tracking (last N turns)
    - Implement entity context tracking (entities mentioned in conversation for follow-up resolution)
    - Implement GraphRAG context injection: when user asks about an entity, auto-fetch its subgraph and inject into agent context
    - Store sessions in Redis with TTL (default 1 hour)
    - _Requirements: 7.4, 9.1_

  - [ ] 18.6 Create CLI and interactive chat interface
    - Create `src/biomedical_kg_mcp/agent/cli.py` with interactive chat loop
    - Support commands: `/help`, `/modules` (list ontology modules), `/context` (show current entities), `/clear` (reset session)
    - Add entry point to pyproject.toml: `biomedical-kg-agent = "biomedical_kg_mcp.agent.cli:main"`
    - User can run: `biomedical-kg-agent` to start interactive session
    - Pretty-print responses with entity links and source attribution
    - _Requirements: 1.7_

  - [ ]* 18.7 Write unit tests for Strands agent layer
    - Test ontology routing logic maps questions to correct modules
    - Test MCP client connections initialize correctly
    - Test multi-agent orchestrator routes single-domain and cross-domain queries correctly
    - Test session memory persists across turns
    - Test GraphRAG context injection fetches relevant subgraph
    - Mock LLM responses and MCP tool calls for deterministic testing

- [ ] 19. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (18 properties defined in design)
- Unit tests validate specific examples and edge cases
- The existing codebase in `src/biomedical_kg_mcp/` should be refactored in-place rather than rewritten from scratch
- All external service connections (Neo4j Aura, Neptune, Databricks, LLM API, Redis) require user-provided credentials via environment variables
- NO Kafka, NO local GraphDB/Ontotext, NO FHIR — these have been explicitly excluded from scope
- pgGraph (Evokoa/pgGraph) is used experimentally for the Supply/Quality module — PostgreSQL with Rust-based graph extension where FK relationships become graph edges automatically
- pgGraph requires PostgreSQL 15+ with the pgGraph extension installed (Docker image or manual install from https://github.com/Evokoa/pgGraph)
- Strands Agents SDK (https://strandsagents.com) provides the agentic workflow layer — user asks questions in natural language, the agent auto-routes to the correct MCP server based on ontology module detection
- Strands runs locally (Python process) connecting to MCP servers via stdio transport — no Lambda/Fargate needed for development

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "1.6"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.5", "2.6"] },
    { "id": 3, "tasks": ["2.2", "2.4"] },
    { "id": 4, "tasks": ["4.1", "5.1", "7.1"] },
    { "id": 5, "tasks": ["4.2", "5.2", "7.2"] },
    { "id": 6, "tasks": ["4.3", "5.3", "5.4", "5.5"] },
    { "id": 7, "tasks": ["8.1", "8.3", "8.5"] },
    { "id": 8, "tasks": ["8.2", "8.4", "8.6"] },
    { "id": 9, "tasks": ["8.7", "8.8"] },
    { "id": 10, "tasks": ["10.1", "11.1"] },
    { "id": 11, "tasks": ["10.2", "11.2"] },
    { "id": 12, "tasks": ["10.3", "10.4"] },
    { "id": 13, "tasks": ["12.1"] },
    { "id": 14, "tasks": ["12.2", "12.3", "12.4"] },
    { "id": 15, "tasks": ["14.1"] },
    { "id": 16, "tasks": ["14.2", "14.3", "14.4"] },
    { "id": 17, "tasks": ["15.1", "15.2", "15.3"] },
    { "id": 18, "tasks": ["15.4", "15.5", "15.6"] },
    { "id": 19, "tasks": ["16A.1"] },
    { "id": 20, "tasks": ["16A.2", "16A.5"] },
    { "id": 21, "tasks": ["16A.3", "16A.4"] },
    { "id": 22, "tasks": ["16A.6"] },
    { "id": 23, "tasks": ["17.1", "17.4"] },
    { "id": 24, "tasks": ["17.2", "17.3"] },
    { "id": 25, "tasks": ["17.5"] },
    { "id": 26, "tasks": ["18.1", "18.2"] },
    { "id": 27, "tasks": ["18.3"] },
    { "id": 28, "tasks": ["18.4", "18.5"] },
    { "id": 29, "tasks": ["18.6", "18.7"] }
  ]
}
```
