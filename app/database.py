"""Redis database connection module with singleton pattern."""

import os
from typing import Optional

import redis.asyncio as redis


class RedisClient:
    """
    Singleton class to manage the Redis connection pool.
    
    Ensures a single shared connection pool across all requests,
    preventing connection overhead in high-concurrency scenarios.
    """
    
    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        """Returns the singleton Redis client instance."""
        if cls._instance is None:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            
            cls._instance = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                max_connections=100,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Gracefully closes the Redis connection pool."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None


async def get_redis() -> redis.Redis:
    """FastAPI dependency for Redis injection."""
    return await RedisClient.get_instance()
