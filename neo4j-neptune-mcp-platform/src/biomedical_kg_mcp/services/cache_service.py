"""
Redis Cache Service

Provides query result caching with entity-aware invalidation.
Supports graceful degradation when Redis is unavailable.
"""

import hashlib
import json
from typing import Optional, Any, List, Set
from redis.asyncio import Redis
from redis.exceptions import RedisError


class CacheService:
    """Redis-based cache with entity-aware invalidation."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.enabled = True
        
        # TTL configurations (seconds)
        self.ttls = {
            "neo4j_query": 300,        # 5 minutes
            "neptune_sparql": 300,     # 5 minutes
            "entity": 3600,            # 1 hour
            "embedding": 86400,        # 24 hours
            "vocab_mapping": 86400,    # 24 hours
        }

    async def get_query_result(
        self, scope: str, query: str, params: Optional[dict] = None
    ) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            scope: Cache scope (neo4j_query, neptune_sparql)
            query: Query string
            params: Query parameters
            
        Returns:
            Cached result or None
        """
        if not self.enabled:
            return None
        
        key = self._query_key(scope, query, params)
        
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except RedisError:
            self._handle_redis_error()
        
        return None

    async def set_query_result(
        self,
        scope: str,
        query: str,
        params: Optional[dict],
        result: Any,
        entity_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Cache query result with entity tracking.
        
        Args:
            scope: Cache scope
            query: Query string
            params: Query parameters
            result: Query result to cache
            entity_ids: Entity IDs referenced in result (for invalidation)
        """
        if not self.enabled:
            return
        
        key = self._query_key(scope, query, params)
        ttl = self.ttls.get(scope, 300)
        
        try:
            # Cache result
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result, default=str)
            )
            
            # Track entity references
            if entity_ids:
                await self._track_entities(key, entity_ids)
        except RedisError:
            self._handle_redis_error()

    async def get_entity(self, entity_type: str, entity_id: str) -> Optional[dict]:
        """
        Get cached entity.
        
        Args:
            entity_type: Type of entity (Drug, Disease, etc.)
            entity_id: Entity identifier
            
        Returns:
            Cached entity or None
        """
        if not self.enabled:
            return None
        
        key = f"entity:{entity_type}:{entity_id}"
        
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except RedisError:
            self._handle_redis_error()
        
        return None

    async def set_entity(
        self, entity_type: str, entity_id: str, entity_data: dict
    ) -> None:
        """
        Cache entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            entity_data: Entity data
        """
        if not self.enabled:
            return
        
        key = f"entity:{entity_type}:{entity_id}"
        ttl = self.ttls["entity"]
        
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(entity_data, default=str)
            )
        except RedisError:
            self._handle_redis_error()

    async def get_embedding(self, node_id: str) -> Optional[List[float]]:
        """
        Get cached embedding.
        
        Args:
            node_id: Node identifier
            
        Returns:
            Embedding vector or None
        """
        if not self.enabled:
            return None
        
        key = f"embedding:{node_id}"
        
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except RedisError:
            self._handle_redis_error()
        
        return None

    async def set_embedding(self, node_id: str, embedding: List[float]) -> None:
        """
        Cache embedding.
        
        Args:
            node_id: Node identifier
            embedding: Embedding vector
        """
        if not self.enabled:
            return
        
        key = f"embedding:{node_id}"
        ttl = self.ttls["embedding"]
        
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(embedding)
            )
        except RedisError:
            self._handle_redis_error()

    async def get_vocab_mapping(
        self, entity_type: str, entity_name: str
    ) -> Optional[dict]:
        """
        Get cached vocabulary mapping.
        
        Args:
            entity_type: Entity type
            entity_name: Entity name
            
        Returns:
            Cached mapping or None
        """
        if not self.enabled:
            return None
        
        name_hash = hashlib.sha256(entity_name.encode()).hexdigest()[:16]
        key = f"vocab:{entity_type}:{name_hash}"
        
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except RedisError:
            self._handle_redis_error()
        
        return None

    async def set_vocab_mapping(
        self, entity_type: str, entity_name: str, mapping: dict
    ) -> None:
        """
        Cache vocabulary mapping.
        
        Args:
            entity_type: Entity type
            entity_name: Entity name
            mapping: Vocabulary mapping
        """
        if not self.enabled:
            return
        
        name_hash = hashlib.sha256(entity_name.encode()).hexdigest()[:16]
        key = f"vocab:{entity_type}:{name_hash}"
        ttl = self.ttls["vocab_mapping"]
        
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(mapping, default=str)
            )
        except RedisError:
            self._handle_redis_error()

    async def invalidate_entity(self, entity_id: str) -> int:
        """
        Invalidate all cache entries referencing an entity.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Number of entries invalidated
        """
        if not self.enabled:
            return 0
        
        tracking_key = f"entity_refs:{entity_id}"
        
        try:
            # Get all cache keys referencing this entity
            cache_keys = await self.redis.smembers(tracking_key)
            
            if cache_keys:
                # Delete cache entries
                await self.redis.delete(*cache_keys)
                # Delete tracking set
                await self.redis.delete(tracking_key)
                return len(cache_keys)
        except RedisError:
            self._handle_redis_error()
        
        return 0

    async def invalidate_entities(self, entity_ids: List[str]) -> int:
        """
        Invalidate cache for multiple entities.
        
        Args:
            entity_ids: List of entity identifiers
            
        Returns:
            Total entries invalidated
        """
        total = 0
        for entity_id in entity_ids:
            count = await self.invalidate_entity(entity_id)
            total += count
        return total

    async def clear_scope(self, scope: str) -> int:
        """
        Clear all entries in a cache scope.
        
        Args:
            scope: Cache scope (neo4j_query, neptune_sparql, etc.)
            
        Returns:
            Number of entries cleared
        """
        if not self.enabled:
            return 0
        
        pattern = f"{scope}:*"
        
        try:
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                
                if cursor == 0:
                    break
            
            return deleted
        except RedisError:
            self._handle_redis_error()
            return 0

    async def _track_entities(self, cache_key: str, entity_ids: List[str]) -> None:
        """
        Track which cache entries reference which entities.
        
        Args:
            cache_key: Cache key
            entity_ids: Referenced entity IDs
        """
        try:
            for entity_id in entity_ids:
                tracking_key = f"entity_refs:{entity_id}"
                await self.redis.sadd(tracking_key, cache_key)
                # Expire tracking set after TTL
                await self.redis.expire(tracking_key, max(self.ttls.values()))
        except RedisError:
            pass  # Non-critical

    def _query_key(self, scope: str, query: str, params: Optional[dict]) -> str:
        """
        Generate cache key for query.
        
        Args:
            scope: Cache scope
            query: Query string
            params: Query parameters
            
        Returns:
            Cache key
        """
        # Create canonical representation
        canonical = query
        if params:
            canonical += "|" + json.dumps(params, sort_keys=True)
        
        # Hash
        query_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return f"{scope}:{query_hash}"

    def _handle_redis_error(self) -> None:
        """Handle Redis errors with graceful degradation."""
        self.enabled = False
        # Log error (in production)
        # Could also set a timer to re-enable after backoff
