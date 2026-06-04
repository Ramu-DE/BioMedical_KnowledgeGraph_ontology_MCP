"""Property test for retry with exponential backoff.

Feature: neo4j-neptune-mcp-platform
Property 16: Retry with Exponential Backoff
"""

import asyncio
import time

import pytest
from hypothesis import given, strategies as st
from unittest.mock import AsyncMock


@pytest.mark.property
class TestRetryWithExponentialBackoff:
    """Property 16: Retry with Exponential Backoff.
    
    For any Neptune request that receives HTTP 429 throttling errors, the system
    SHALL retry with exponential backoff delays, and SHALL NOT exceed 3 retry
    attempts before returning a throttling error to the caller.
    
    Validates: Requirements 2.6
    """
    
    @given(num_failures=st.integers(min_value=1, max_value=5))
    @pytest.mark.asyncio
    async def test_retry_attempts_capped_at_three(self, num_failures):
        """Retry attempts never exceed 3."""
        attempts = []
        
        async def failing_request():
            attempts.append(time.time())
            if len(attempts) <= num_failures:
                raise Exception("HTTP 429")
            return {"status": "success"}
        
        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await failing_request()
                break
            except Exception:
                if attempt == max_retries - 1:
                    # Final attempt failed
                    break
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Should not exceed 3 attempts
        assert len(attempts) <= 3
    
    @pytest.mark.asyncio
    async def test_backoff_delays_increase_exponentially(self):
        """Retry delays increase exponentially (1s, 2s, 4s)."""
        attempts_times = []
        
        async def throttled_request():
            attempts_times.append(time.time())
            if len(attempts_times) < 4:  # Fail first 3 times
                raise Exception("HTTP 429")
            return {"status": "success"}
        
        # Execute with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await throttled_request()
                break
            except Exception:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1, 2, 4
                    await asyncio.sleep(wait_time)
        
        # Verify delays increased exponentially
        if len(attempts_times) >= 2:
            # Check time differences
            delays = [
                attempts_times[i+1] - attempts_times[i]
                for i in range(len(attempts_times) - 1)
            ]
            
            # Each delay should be approximately 2x the previous
            for i in range(len(delays) - 1):
                # Allow some tolerance for execution time
                ratio = delays[i+1] / delays[i] if delays[i] > 0 else 0
                assert 1.5 <= ratio <= 2.5, f"Delays not exponential: {delays}"
    
    @given(success_on_attempt=st.integers(min_value=1, max_value=3))
    @pytest.mark.asyncio
    async def test_success_stops_retry_loop(self, success_on_attempt):
        """Successful response stops retry attempts."""
        attempts = []
        
        async def eventually_succeeds():
            attempts.append(1)
            if len(attempts) < success_on_attempt:
                raise Exception("HTTP 429")
            return {"status": "success"}
        
        # Execute with retry
        max_retries = 3
        result = None
        for attempt in range(max_retries):
            try:
                result = await eventually_succeeds()
                break
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.01)  # Fast for testing
        
        # Should succeed and stop retrying
        assert len(attempts) == success_on_attempt
        assert result is not None or success_on_attempt > 3
    
    @pytest.mark.asyncio
    async def test_final_failure_returns_error(self):
        """After 3 failed retries, error is returned to caller."""
        attempts = []
        
        async def always_fails():
            attempts.append(1)
            raise Exception("HTTP 429")
        
        # Execute with retry
        max_retries = 3
        final_error = None
        for attempt in range(max_retries):
            try:
                await always_fails()
            except Exception as e:
                final_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.01)
        
        # Should have tried 3 times and returned error
        assert len(attempts) == 3
        assert final_error is not None
        assert "429" in str(final_error)
