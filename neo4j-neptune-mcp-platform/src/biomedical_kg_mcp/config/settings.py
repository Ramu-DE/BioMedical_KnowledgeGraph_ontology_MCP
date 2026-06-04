"""Configuration settings for the Neo4j-Neptune MCP Platform."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jAuraSettings(BaseSettings):
    """Neo4j Aura DB configuration."""
    
    model_config = SettingsConfigDict(env_prefix="NEO4J_")
    
    uri: str = Field(..., description="Neo4j Aura connection URI (bolt+s://...)")
    user: str = Field(default="neo4j", description="Username")
    password: str = Field(..., description="Password")
    database: str = Field(default="neo4j", description="Database name")
    max_connection_pool_size: int = Field(default=50, description="Max connections")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")


class NeptuneSettings(BaseSettings):
    """AWS Neptune configuration."""
    
    model_config = SettingsConfigDict(env_prefix="NEPTUNE_")
    
    cluster_endpoint: str = Field(..., description="Neptune cluster endpoint")
    port: int = Field(default=8182, description="Neptune port")
    region: str = Field(default="us-east-1", description="AWS region")
    iam_role_arn: str = Field(default="", description="IAM role for bulk loader")
    use_iam_auth: bool = Field(default=True, description="Use IAM authentication")


class DatabricksSettings(BaseSettings):
    """Databricks workspace configuration."""
    
    model_config = SettingsConfigDict(env_prefix="DATABRICKS_")
    
    workspace_url: str = Field(..., description="Databricks workspace URL")
    access_token: str = Field(..., description="Personal Access Token")
    cluster_id: str = Field(default="", description="Compute cluster ID")
    warehouse_id: str = Field(default="", description="SQL warehouse ID")
    catalog: str = Field(default="biomedkg", description="Unity Catalog name")
    schema: str = Field(default="semantic_medallion", description="Schema name")


class LLMSettings(BaseSettings):
    """LLM API configuration."""
    
    model_config = SettingsConfigDict(env_prefix="LLM_")
    
    api_key: str = Field(..., description="LLM API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="API base URL")
    model: str = Field(default="text-embedding-3-small", description="Embedding model")
    chat_model: str = Field(default="gpt-4o-mini", description="Chat model")
    max_tokens: int = Field(default=4096, description="Max tokens per request")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    embedding_dimensions: int = Field(default=1536, description="Embedding dimensions")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts")


class RedisSettings(BaseSettings):
    """Redis cache configuration."""
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    password: str = Field(default="", description="Redis password")
    db: int = Field(default=0, description="Database number")
    query_ttl: int = Field(default=300, description="Query cache TTL in seconds")
    entity_ttl: int = Field(default=3600, description="Entity cache TTL in seconds")
    embedding_ttl: int = Field(default=86400, description="Embedding cache TTL in seconds")


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")
    
    api_keys: str = Field(default="", description="Comma-separated API keys")
    rate_limit_admin: int = Field(default=500, description="Admin tier: requests/min")
    rate_limit_ai_agent: int = Field(default=200, description="AI agent tier: requests/min")
    rate_limit_read_only: int = Field(default=100, description="Read-only tier: requests/min")
    rate_limit_write: int = Field(default=20, description="Write tier: requests/min")


class PlatformSettings(BaseSettings):
    """Root configuration aggregating all settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    neo4j: Neo4jAuraSettings = Field(default_factory=Neo4jAuraSettings)
    neptune: NeptuneSettings = Field(default_factory=NeptuneSettings)
    databricks: DatabricksSettings = Field(default_factory=DatabricksSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
    environment: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")
    base_iri: str = Field(default="https://biomedkg.org/ontology/", description="Base IRI namespace")
