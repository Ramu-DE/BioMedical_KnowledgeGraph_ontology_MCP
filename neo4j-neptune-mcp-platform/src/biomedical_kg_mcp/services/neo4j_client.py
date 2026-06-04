"""Neo4j Aura client service with async driver and circuit breaker."""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class Neo4jClient:
    """
    Neo4j Aura client with connection pooling, timeout handling, and circuit breaker.
    
    Features:
    - Async driver with bolt+s:// connection
    - Connection pooling (max 50 connections)
    - Query timeout (10s default)
    - Circuit breaker (5 failures → open for 30s)
    - Health checks
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        connection_timeout: int = 30,
        query_timeout: int = 10,
    ):
        """
        Initialize Neo4j client.
        
        Args:
            uri: Neo4j Aura URI (bolt+s://...)
            user: Username
            password: Password
            database: Database name
            max_connection_pool_size: Max connections in pool
            connection_timeout: Connection timeout in seconds
            query_timeout: Query timeout in seconds
        """
        self.uri = uri
        self.database = database
        self.query_timeout = query_timeout
        
        # Initialize async driver
        self._driver: Optional[AsyncDriver] = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout,
        )
        
        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = 5
        self._recovery_timeout = 30  # seconds
        self._last_failure_time: Optional[datetime] = None
        self._half_open_successes = 0
        self._half_open_threshold = 3
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute Cypher query with timeout and circuit breaker.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            timeout: Query timeout in seconds (overrides default)
            
        Returns:
            List of result records as dictionaries
        """
        # Check circuit breaker
        if not self._check_circuit():
            raise ConnectionError(
                f"Circuit breaker is {self._circuit_state.value}. "
                f"Service unavailable. Retry after {self._recovery_timeout}s."
            )
        
        timeout = timeout or self.query_timeout
        
        try:
            async with self._driver.session(database=self.database) as session:
                result = await asyncio.wait_for(
                    self._run_query(session, query, parameters),
                    timeout=timeout
                )
                self._on_success()
                return result
        
        except asyncio.TimeoutError:
            self._on_failure()
            raise TimeoutError(f"Query exceeded timeout of {timeout}s")
        
        except Exception as e:
            self._on_failure()
            raise
    
    async def _run_query(
        self,
        session: AsyncSession,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Run query and convert records to dictionaries."""
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records
    
    async def health_check(self) -> bool:
        """
        Check Neo4j connection health.
        
        Returns:
            True if connection is healthy
        """
        try:
            await self.execute_query("RETURN 1 as health", timeout=5)
            return True
        except Exception:
            return False
    
    async def get_schema(self) -> Dict[str, Any]:
        """
        Get graph schema (node labels, relationship types, property keys).
        
        Returns:
            Schema information
        """
        schema = {
            "node_labels": [],
            "relationship_types": [],
            "property_keys": [],
        }
        
        # Get node labels
        labels_result = await self.execute_query("CALL db.labels()")
        schema["node_labels"] = [r["label"] for r in labels_result]
        
        # Get relationship types
        rels_result = await self.execute_query("CALL db.relationshipTypes()")
        schema["relationship_types"] = [r["relationshipType"] for r in rels_result]
        
        # Get property keys
        props_result = await self.execute_query("CALL db.propertyKeys()")
        schema["property_keys"] = [r["propertyKey"] for r in props_result]
        
        return schema
    
    def _check_circuit(self) -> bool:
        """Check if circuit breaker allows requests."""
        if self._circuit_state == CircuitState.CLOSED:
            return True
        
        if self._circuit_state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self._recovery_timeout:
                    # Move to half-open state
                    self._circuit_state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                    return True
            return False
        
        # HALF_OPEN state: allow requests
        return True
    
    def _on_success(self) -> None:
        """Handle successful request."""
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self._half_open_threshold:
                # Service recovered, close circuit
                self._circuit_state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._circuit_state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed request."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._circuit_state == CircuitState.HALF_OPEN:
            # Fail fast back to open
            self._circuit_state = CircuitState.OPEN
        elif self._failure_count >= self._failure_threshold:
            # Open circuit
            self._circuit_state = CircuitState.OPEN
    
    async def close(self) -> None:
        """Close driver and connections."""
        if self._driver:
            await self._driver.close()
