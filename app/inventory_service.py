"""Inventory service with safe and unsafe purchase methods."""

import asyncio
from redis.asyncio import Redis


class InventoryService:
    """
    Service layer for inventory management operations.
    
    Demonstrates race condition vulnerability (unsafe) vs
    atomic operations using Lua scripts (safe).
    """

    STOCK_KEY = "product_stock"

    def __init__(self, redis_client: Redis) -> None:
        self.redis = redis_client

    async def purchase_item_unsafe(self) -> bool:
        """
        Vulnerable purchase method demonstrating race conditions.
        
        Uses non-atomic read-check-write pattern that allows
        multiple concurrent requests to read the same stock value
        before any of them decrements it.
        
        Returns:
            bool: True if purchase appeared successful, False if out of stock.
        """
        stock = await self.redis.get(self.STOCK_KEY)
        stock = int(stock) if stock else 0

        if stock > 0:
            # Simulated processing delay amplifies race condition window
            await asyncio.sleep(0.05)
            await self.redis.set(self.STOCK_KEY, stock - 1)
            return True

        return False

    async def purchase_item_safe(self) -> bool:
        """
        Thread-safe purchase using Redis Lua script for atomicity.
        
        The entire check-and-decrement operation executes as a single
        atomic transaction within Redis, preventing race conditions.
        
        Returns:
            bool: True if purchase successful, False if out of stock.
        """
        lua_script = """
        local stock = redis.call('GET', KEYS[1])
        if stock and tonumber(stock) > 0 then
            redis.call('DECR', KEYS[1])
            return 1
        end
        return 0
        """
        result = await self.redis.eval(lua_script, 1, self.STOCK_KEY)
        return bool(result)

    async def reset_stock(self, amount: int = 50) -> None:
        """Resets product stock to specified amount."""
        await self.redis.set(self.STOCK_KEY, amount)

    async def get_stock(self) -> int:
        """Returns current stock level."""
        stock = await self.redis.get(self.STOCK_KEY)
        return int(stock) if stock else 0
