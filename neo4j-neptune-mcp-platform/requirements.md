# Requirements Document

## Introduction

This document specifies the requirements for the Neo4j-Neptune MCP Platform — a Model Context Protocol (MCP) Server Platform that bridges Neo4j (local LPG for development/exploration) with AWS Neptune (production RDF + openCypher), integrated with a Databricks Lakehouse Semantic Medallion architecture. The platform follows a semantic ontology architecture for a BioMedical Knowledge Graph containing 20 node types and 30 relationship types across oncology, genomics, clinical trials, and pharmacology domains.

The platform exposes tools via MCP (JSON-RPC 2.0) that AI agents can use to query, sync, validate, catalog, and generate embeddings from the biomedical knowledge graph.

## Glossary

- **MCP_Platform**: The complete Model Context Protocol Server Platform comprising multiple MCP servers that expose JSON-RPC 2.0 tools for AI agent interaction with the biomedical knowledge graph
- **Neo4j_MCP_Server**: The MCP server providing local Labeled Property Graph (LPG) query tools via Cypher for development and exploration against a local Docker-hosted Neo4j instance
- **Neptune_MCP_Server**: The MCP server providing production graph database tools supporting both SPARQL 1.1 (RDF) and openCypher (LPG) query interfaces against AWS Neptune
- **Graph_Sync_Server**: The MCP server managing bidirectional synchronization between Neo4j and Neptune with validation, IRI minting, vocabulary alignment, and conflict resolution
- **Lakehouse_MCP_Server**: The MCP server managing the Databricks Semantic Medallion architecture (Bronze → Silver → Gold → Graph layers)
- **SHACL_Validator**: The component that validates RDF graph data against SHACL (Shapes Constraint Language) shape definitions before publishing to Neptune
- **IRI_Minter**: The component that generates stable Internationalized Resource Identifiers following W3C DCAT patterns using the namespace https://biomedkg.org/ontology/{type}/{id}
- **Vocabulary_Aligner**: The component that maps biomedical entities to controlled vocabularies including SNOMED-CT, ICD-10, MedDRA, LOINC, RxNorm, NCIt, CDISC, and BRIDG
- **Semantic_Medallion**: The layered data architecture in Databricks comprising Bronze (raw), Silver (structured with stable IRIs), and Gold (RDF-harmonized) tiers
- **DCAT_Catalog**: The W3C Data Catalog Vocabulary implementation providing self-describing dataset metadata with PROV-O provenance triples
- **GraphRAG_Engine**: The component enabling Retrieval-Augmented Generation through knowledge graph embeddings, community detection, and subgraph extraction
- **Neptune_Streams**: AWS Neptune's change data capture mechanism used for detecting graph mutations and triggering sync operations (replaces Kafka)
- **SigV4_Authenticator**: The AWS Signature Version 4 authentication module for signing requests to Neptune endpoints
- **Ontology_Module**: A modular ontology component (Foundation, Commercial, Clinical, Medical Affairs, Patient, Supply/Quality, or Governance) that defines domain-specific classes and properties
- **Delta_Lake**: The Databricks storage layer providing ACID transactions, schema enforcement, and time travel for the lakehouse data platform
- **Redis_Cache**: The Redis-based query caching layer for improving response times on repeated graph queries

## Requirements

### Requirement 1: Neo4j MCP Server — Local LPG Query Interface

**User Story:** As an AI agent developer, I want to query the biomedical knowledge graph via Cypher through MCP tools, so that I can explore relationships, find paths, and detect communities in the local development graph.

#### Acceptance Criteria

1. WHEN a Cypher query is submitted via the `neo4j_query` tool, THE Neo4j_MCP_Server SHALL execute the query against the local Neo4j instance and return results as structured JSON within 10 seconds
2. WHEN a path-finding request is submitted with source and target node identifiers, THE Neo4j_MCP_Server SHALL compute shortest paths using Dijkstra or BFS algorithms and return the path with intermediate nodes and relationship types
3. WHEN a community detection request is submitted with an algorithm parameter (Louvain, Label Propagation, or Weakly Connected Components), THE Neo4j_MCP_Server SHALL execute the graph algorithm and return community assignments for each node
4. WHEN a node expansion request is submitted with a node identifier and depth parameter, THE Neo4j_MCP_Server SHALL return the subgraph within the specified traversal depth including all nodes and relationships
5. IF a Cypher query exceeds the configured timeout of 10 seconds, THEN THE Neo4j_MCP_Server SHALL terminate the query and return a timeout error with the partial execution time
6. IF the Neo4j connection is unavailable, THEN THE Neo4j_MCP_Server SHALL return a connection error with the last known health status and retry recommendation
7. THE Neo4j_MCP_Server SHALL register all tools via the MCP `tools/list` method with complete JSON Schema input definitions following the JSON-RPC 2.0 protocol

### Requirement 2: AWS Neptune MCP Server — Production Graph Query Interface

**User Story:** As an AI agent developer, I want to query the production biomedical knowledge graph via both SPARQL and openCypher through MCP tools, so that I can leverage the full semantic richness of the RDF ontology and the familiarity of Cypher syntax.

#### Acceptance Criteria

1. WHEN a SPARQL 1.1 query is submitted via the `neptune_sparql` tool, THE Neptune_MCP_Server SHALL execute the query against the Neptune SPARQL endpoint and return results in SPARQL JSON Results format
2. WHEN an openCypher query is submitted via the `neptune_cypher` tool, THE Neptune_MCP_Server SHALL execute the query against the Neptune openCypher endpoint and return results as structured JSON
3. THE Neptune_MCP_Server SHALL authenticate all requests to Neptune using AWS IAM SigV4 request signing with credentials from the configured AWS profile or IAM role
4. WHEN a bulk load request is submitted with an S3 URI, THE Neptune_MCP_Server SHALL initiate a Neptune bulk loader job and return the job identifier for status tracking
5. WHEN a bulk load status request is submitted with a job identifier, THE Neptune_MCP_Server SHALL query the Neptune loader status endpoint and return the current job state including records loaded and errors encountered
6. IF a Neptune request fails with a throttling error (HTTP 429), THEN THE Neptune_MCP_Server SHALL retry the request using exponential backoff with a maximum of 3 retries
7. IF the Neptune cluster endpoint is unreachable, THEN THE Neptune_MCP_Server SHALL return a connection error with cluster status information and the configured endpoint URL
8. THE Neptune_MCP_Server SHALL support parameterized queries to prevent injection attacks in both SPARQL and openCypher interfaces

### Requirement 3: Graph Sync MCP Server — Bidirectional Neo4j ↔ Neptune Synchronization

**User Story:** As a knowledge engineer, I want to synchronize graph data between the local Neo4j development environment and production Neptune, so that validated local changes can be promoted to production and production data can be pulled for local analysis.

#### Acceptance Criteria

1. WHEN a sync-to-Neptune request is submitted for a set of nodes or subgraph, THE Graph_Sync_Server SHALL validate the data against SHACL shapes, mint IRIs, align vocabularies, and publish the validated RDF triples to Neptune
2. WHEN a sync-from-Neptune request is submitted with a SPARQL CONSTRUCT or named graph identifier, THE Graph_Sync_Server SHALL retrieve the RDF data from Neptune, convert it to LPG format, and load it into the local Neo4j instance
3. WHEN the SHACL_Validator receives graph data for validation, THE SHACL_Validator SHALL validate all triples against the configured SHACL shape definitions and return a validation report listing all conformance violations with severity levels (Violation, Warning, Info)
4. WHEN the IRI_Minter receives an entity for IRI generation, THE IRI_Minter SHALL generate a stable IRI following the pattern `https://biomedkg.org/ontology/{type}/{id}` where type maps to the ontology class and id is a deterministic identifier derived from the entity properties
5. WHEN the Vocabulary_Aligner receives a biomedical entity, THE Vocabulary_Aligner SHALL attempt to map the entity to at least one controlled vocabulary (SNOMED-CT, ICD-10, MedDRA, LOINC, RxNorm, NCIt, CDISC, or BRIDG) and return the mapping with confidence score
6. WHEN a conflict is detected between Neo4j and Neptune versions of the same entity, THE Graph_Sync_Server SHALL apply last-writer-wins resolution using timestamps and record the conflict details in an audit trail with both previous and new values
7. THE Graph_Sync_Server SHALL subscribe to Neptune Streams for change data capture to detect mutations in the production graph and queue sync operations
8. IF SHACL validation fails for any entity in a sync batch, THEN THE Graph_Sync_Server SHALL reject the entire batch, return the validation report, and record the failed sync attempt in the audit log

### Requirement 4: Databricks Lakehouse MCP Server — Semantic Medallion Pipeline

**User Story:** As a data engineer, I want to run the semantic medallion pipeline (Bronze → Silver → Gold → Graph) through MCP tools, so that raw biomedical data is progressively refined into RDF-harmonized knowledge graph data.

#### Acceptance Criteria

1. WHEN a Bronze layer ingestion request is submitted with a data source specification (CSV file path, API endpoint, or external registry URL), THE Lakehouse_MCP_Server SHALL ingest the raw data into the Bronze Delta Lake table with source metadata and ingestion timestamp
2. WHEN a Silver layer processing request is submitted for a Bronze dataset, THE Lakehouse_MCP_Server SHALL apply entity resolution, deduplication, and IRI minting to produce structured records with stable IRIs in the Silver Delta Lake table
3. WHEN a Gold layer transformation request is submitted for a Silver dataset, THE Lakehouse_MCP_Server SHALL map the structured data to the shared ontology modules (Foundation, Commercial, Clinical, Medical Affairs, Patient, Supply/Quality, Governance), generate RDF triples, and store the results in the Gold Delta Lake table
4. WHEN a full pipeline execution request is submitted with a data source, THE Lakehouse_MCP_Server SHALL execute the Bronze → Silver → Gold stages sequentially and return a pipeline execution summary with record counts and processing time for each stage
5. WHEN a pipeline stage fails, THE Lakehouse_MCP_Server SHALL record the failure with error details, mark the affected records, and allow re-execution of the failed stage without reprocessing completed stages
6. THE Lakehouse_MCP_Server SHALL integrate with Databricks Delta Lake for ACID transactions, schema enforcement, and time-travel capabilities across all medallion layers
7. WHEN a Gold layer dataset is marked as ready for graph loading, THE Lakehouse_MCP_Server SHALL export the RDF triples to S3 in N-Triples format suitable for Neptune bulk loading

### Requirement 5: SHACL Shape Validation Service

**User Story:** As a knowledge engineer, I want to validate graph data against SHACL shapes before publishing to production, so that data quality and ontology conformance are enforced consistently.

#### Acceptance Criteria

1. WHEN a validation request is submitted with RDF data and a SHACL shapes graph, THE SHACL_Validator SHALL validate the data graph against all applicable shape constraints and return a SHACL Validation Report in Turtle or JSON-LD format
2. WHEN the SHACL shapes define cardinality constraints (sh:minCount, sh:maxCount), THE SHACL_Validator SHALL verify that each focus node has the correct number of values for constrained properties
3. WHEN the SHACL shapes define datatype constraints (sh:datatype), THE SHACL_Validator SHALL verify that all literal values conform to the specified XSD datatype
4. WHEN the SHACL shapes define class constraints (sh:class), THE SHACL_Validator SHALL verify that all object values are instances of the specified RDF class
5. IF validation produces zero Violation-severity results, THEN THE SHACL_Validator SHALL report the data as conformant and approve the data for sync to Neptune
6. THE SHACL_Validator SHALL support SHACL shapes for all 20 node types in the biomedical knowledge graph including Disease, Drug, Gene, Protein, Pathway, Clinical_Trial, Adverse_Event, Anatomy, Biological_Process, Molecular_Function, Biomarker, Cell_Type, Phenotype, Exposure, Research_Paper, Researcher, Institution, Entity, Cluster, and Cluster_Summary

### Requirement 6: DCAT Catalog Service

**User Story:** As a data steward, I want self-describing dataset metadata with provenance tracking, so that consumers can discover available datasets, understand their lineage, and assess data quality.

#### Acceptance Criteria

1. WHEN a dataset is published to any medallion layer or to Neptune, THE DCAT_Catalog SHALL create or update a DCAT Dataset entry with title, description, distribution information, temporal coverage, and spatial coverage metadata
2. WHEN a dataset entry is created, THE DCAT_Catalog SHALL generate PROV-O provenance triples capturing the creation activity, responsible agent, source datasets used, and generation timestamp
3. WHEN a catalog search request is submitted with keyword, theme, or temporal filters, THE DCAT_Catalog SHALL return matching DCAT Dataset entries ordered by relevance
4. THE DCAT_Catalog SHALL expose catalog contents as RDF triples conforming to the W3C DCAT 2.0 vocabulary and accessible via the Neptune SPARQL endpoint
5. WHEN a dataset undergoes a transformation (Bronze → Silver → Gold), THE DCAT_Catalog SHALL record the derivation relationship (prov:wasDerivedFrom) linking the output dataset to its input dataset

### Requirement 7: GraphRAG Enablement

**User Story:** As an AI application developer, I want to generate and retrieve knowledge graph embeddings and extract relevant subgraphs, so that I can build Retrieval-Augmented Generation pipelines grounded in the biomedical knowledge graph.

#### Acceptance Criteria

1. WHEN an embedding generation request is submitted for a set of nodes or a named subgraph, THE GraphRAG_Engine SHALL compute knowledge graph embeddings using node2vec or TransE algorithms and store the resulting vectors with their associated node identifiers
2. WHEN an embedding retrieval request is submitted with a query vector and a top-k parameter, THE GraphRAG_Engine SHALL perform approximate nearest neighbor search and return the top-k most similar nodes with their similarity scores
3. WHEN a community detection request is submitted, THE GraphRAG_Engine SHALL identify communities in the knowledge graph using the Louvain algorithm and return community assignments with summary descriptions generated from member node properties
4. WHEN a subgraph extraction request is submitted with a seed entity and relevance criteria (hop distance, relationship types, minimum confidence), THE GraphRAG_Engine SHALL extract the relevant subgraph and return it in a format suitable for LLM context injection
5. THE GraphRAG_Engine SHALL maintain an embedding index that is updated when new nodes are added to the Gold layer or when the graph structure changes in Neptune
6. IF embedding generation fails for specific nodes due to disconnected components or insufficient neighborhood information, THEN THE GraphRAG_Engine SHALL log the affected nodes and return a partial result with a warning indicating which nodes were excluded

### Requirement 8: IRI Minting and Controlled Vocabulary Alignment

**User Story:** As a semantic web engineer, I want entities to receive stable, deterministic IRIs mapped to standard biomedical vocabularies, so that the knowledge graph is interoperable with external biomedical datasets and ontologies.

#### Acceptance Criteria

1. THE IRI_Minter SHALL generate IRIs following the pattern `https://biomedkg.org/ontology/{OntologyClass}/{DeterministicId}` where OntologyClass is derived from the ontology module and DeterministicId is a URL-safe hash of the entity's identifying properties
2. WHEN the same entity properties are submitted multiple times, THE IRI_Minter SHALL produce the identical IRI (idempotent minting) ensuring referential stability across sync operations
3. WHEN a Drug entity is submitted for vocabulary alignment, THE Vocabulary_Aligner SHALL map it to RxNorm codes and return the RxNorm CUI with mapping confidence
4. WHEN a Disease entity is submitted for vocabulary alignment, THE Vocabulary_Aligner SHALL map it to ICD-10 codes and SNOMED-CT concept identifiers with mapping confidence
5. WHEN an Adverse Event entity is submitted for vocabulary alignment, THE Vocabulary_Aligner SHALL map it to MedDRA Preferred Terms (PT) and Lowest Level Terms (LLT) with mapping confidence
6. WHEN a Gene or Protein entity is submitted for vocabulary alignment, THE Vocabulary_Aligner SHALL map it to NCIt concept codes and UniProt identifiers with mapping confidence
7. IF the Vocabulary_Aligner cannot find a mapping with confidence above 0.7, THEN THE Vocabulary_Aligner SHALL flag the entity for manual review and record the best candidate mapping with its confidence score

### Requirement 9: Query Caching with Redis

**User Story:** As a platform operator, I want frequently executed graph queries to be cached, so that response times are reduced and backend load is minimized for repeated access patterns.

#### Acceptance Criteria

1. WHEN a query result is returned from Neo4j or Neptune, THE Redis_Cache SHALL store the result with a cache key derived from the query text and parameters, using the configured TTL (300 seconds for queries, 3600 seconds for entity lookups)
2. WHEN an identical query is submitted within the TTL window, THE Redis_Cache SHALL return the cached result without executing the query against the graph database
3. WHEN a sync operation modifies entities in Neptune or Neo4j, THE Redis_Cache SHALL invalidate all cache entries that reference the modified entities
4. IF Redis is unavailable, THEN THE MCP_Platform SHALL bypass the cache layer and execute queries directly against the graph database without returning an error to the caller

### Requirement 10: Platform Authentication and Security

**User Story:** As a platform administrator, I want secure access to all MCP server endpoints, so that only authorized AI agents and users can query and modify the knowledge graph.

#### Acceptance Criteria

1. THE MCP_Platform SHALL authenticate all incoming MCP tool invocations using API key validation via the X-API-Key header
2. THE Neptune_MCP_Server SHALL authenticate all outbound requests to AWS Neptune using IAM SigV4 request signing with credentials sourced from the AWS credential chain (environment variables, instance profile, or assumed role)
3. WHEN an unauthenticated request is received, THE MCP_Platform SHALL return a JSON-RPC 2.0 error response with code -32600 (Invalid Request) and a message indicating authentication failure
4. THE MCP_Platform SHALL enforce rate limiting per API key with configurable tiers: admin (500 requests/minute), ai-agent (200 requests/minute), read-only (100 requests/minute), and write (20 requests/minute)
5. THE MCP_Platform SHALL log all tool invocations with timestamp, tool name, caller identity, execution duration, and success/failure status for audit purposes

### Requirement 11: Neptune Streams Change Data Capture

**User Story:** As a platform engineer, I want to capture graph mutations from Neptune using Neptune Streams, so that downstream systems can react to changes without polling and sync operations can be triggered automatically.

#### Acceptance Criteria

1. WHEN Neptune Streams emits a change record (ADD or REMOVE of a triple), THE Graph_Sync_Server SHALL read the stream record and determine if a sync operation to Neo4j is required based on the configured sync rules
2. WHEN a stream record indicates a new entity was added to Neptune, THE Graph_Sync_Server SHALL convert the RDF representation to LPG format and create the corresponding node in Neo4j with all mapped properties
3. WHEN a stream record indicates a relationship was added to Neptune, THE Graph_Sync_Server SHALL create the corresponding relationship in Neo4j between the mapped source and target nodes
4. THE Graph_Sync_Server SHALL maintain a stream checkpoint (commit number) in persistent storage to enable resumption after restarts without reprocessing previously consumed records
5. IF the stream reader falls behind the Neptune Streams retention window, THEN THE Graph_Sync_Server SHALL log a warning, initiate a full resync for affected named graphs, and reset the checkpoint to the current stream position

### Requirement 12: Ontology Module Management

**User Story:** As a knowledge engineer, I want to manage the core ontology modules through MCP tools, so that the semantic schema can be queried, versioned, and applied to data transformations.

#### Acceptance Criteria

1. WHEN an ontology listing request is submitted, THE MCP_Platform SHALL return the available ontology modules (Foundation, Commercial, Clinical, Medical_Affairs, Patient, Supply_Quality, Governance) with their namespace URIs and version identifiers
2. WHEN an ontology class lookup is submitted with an entity type, THE MCP_Platform SHALL return the ontology class definition including properties, cardinality constraints, and parent classes from the appropriate ontology module
3. WHEN a source-to-ontology mapping request is submitted with a CSV column schema, THE MCP_Platform SHALL return the recommended ontology property mappings with data type transformations for use in the Silver → Gold pipeline stage
4. THE MCP_Platform SHALL store ontology modules as OWL files in the Neptune named graph `https://biomedkg.org/ontology/` and serve them through the SPARQL endpoint
