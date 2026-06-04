"""
Rate Limiting Service

Implements sliding window rate limiting per API key tier using Redis.
"""

import time
from typing import Optional
from redis.asyncio import Redis
from redis.exceptions import RedisError
from .auth_service import APIKeyTier


class RateLimiter:
    """Redis-based rate limiter with sliding window."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.enabled = True
        
        # Rate limits per tier (requests per minute)
        self.limits = {
            APIKeyTier.ADMIN: 500,
            APIKeyTier.AI_AGENT: 200,
            APIKeyTier.READ_ONLY: 100,
            APIKeyTier.WRITE: 20,
        }

    async def check_rate_limit(self, key_id: str, tier: APIKeyTier) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            key_id: API key identifier
            tier: API key tier
            
        Returns:
            (allowed, current_count, limit)
        """
        if not self.enabled:
            return True, 0, 0
        
        limit = self.limits.get(tier, 100)
        window = 60  # 1 minute window
        
        key = f"ratelimit:{key_id}"
        now = int(time.time())
        window_start = now - window
        
        try:
            # Remove old entries outside window
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            count = await self.redis.zcard(key)
            
            if count >= limit:
                return False, count, limit
            
            # Add current request
            await self.redis.zadd(key, {str(now): now})
            await self.redis.expire(key, window + 10)  # Expire after window
            
            return True, count + 1, limit
            
        except RedisError:
            self.enabled = False
            return True, 0, 0  # Allow on Redis failure

    async def get_remaining(self, key_id: str, tier: APIKeyTier) -> tuple[int, int]:
        """
        Get remaining requests in window.
        
        Args:
            key_id: API key identifier
            tier: API key tier
            
        Returns:
            (remaining, limit)
        """
        if not self.enabled:
            return 0, 0
        
        limit = self.limits.get(tier, 100)
        window = 60
        
        key = f"ratelimit:{key_id}"
        now = int(time.time())
        window_start = now - window
        
        try:
            await self.redis.zremrangebyscore(key, 0, window_start)
            count = await self.redis.zcard(key)
            remaining = max(0, limit - count)
            return remaining, limit
        except RedisError:
            return 0, 0
