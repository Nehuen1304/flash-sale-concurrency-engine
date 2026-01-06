"""FastAPI application entry point with purchase simulation endpoints."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from redis.asyncio import Redis

from app.database import get_redis, RedisClient
from app.inventory_service import InventoryService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    yield
    await RedisClient.close()


app = FastAPI(
    title="Flash Sale Concurrency Engine",
    description="Demonstrates race conditions vs atomic operations in high-concurrency scenarios.",
    version="1.0.0",
    lifespan=lifespan,
)


async def get_inventory_service(redis: Redis = Depends(get_redis)) -> InventoryService:
    """Dependency injection for InventoryService."""
    return InventoryService(redis)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes probes."""
    return {"status": "healthy"}


@app.get("/stock")
async def get_stock(service: InventoryService = Depends(get_inventory_service)):
    """Returns current stock level."""
    stock = await service.get_stock()
    return {"current_stock": stock}


@app.post("/stock/reset")
async def reset_stock(
    amount: int = 50,
    service: InventoryService = Depends(get_inventory_service),
):
    """Resets stock to specified amount for testing."""
    await service.reset_stock(amount)
    return {"message": f"Stock reset to {amount}", "new_stock": amount}


@app.post("/purchase/unsafe")
async def purchase_unsafe(service: InventoryService = Depends(get_inventory_service)):
    """
    Simulates purchase using vulnerable method.
    
    This endpoint demonstrates how race conditions cause overselling
    when multiple concurrent requests occur.
    """
    success = await service.purchase_item_unsafe()
    if not success:
        raise HTTPException(status_code=400, detail="Out of stock")
    return {"success": True, "method": "unsafe"}


@app.post("/purchase/safe")
async def purchase_safe(service: InventoryService = Depends(get_inventory_service)):
    """
    Simulates purchase using atomic Lua script.
    
    This endpoint demonstrates proper concurrency handling
    with guaranteed stock integrity.
    """
    success = await service.purchase_item_safe()
    if not success:
        raise HTTPException(status_code=400, detail="Out of stock")
    return {"success": True, "method": "safe"}
