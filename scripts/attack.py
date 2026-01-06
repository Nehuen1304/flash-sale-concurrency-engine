"""
Concurrent attack script to simulate Flash Sale traffic.

This script launches hundreds of simultaneous HTTP requests to demonstrate
the difference between race-condition-vulnerable and atomic purchase methods.
"""

import asyncio
import time

import aiohttp


# Configuration
CONCURRENT_USERS = 500
INITIAL_STOCK = 50
BASE_URL = "http://localhost:8000"


async def make_purchase(session: aiohttp.ClientSession, endpoint: str) -> int:
    """Attempts a single purchase and returns the HTTP status code."""
    try:
        async with session.post(f"{BASE_URL}/purchase/{endpoint}") as response:
            return response.status
    except Exception:
        return 500


async def run_attack(endpoint: str) -> tuple[int, int, float]:
    """
    Launches concurrent purchase requests against the specified endpoint.
    
    Returns:
        tuple: (successful_purchases, final_stock, duration_seconds)
    """
    async with aiohttp.ClientSession() as session:
        # Reset stock before attack
        await session.post(f"{BASE_URL}/stock/reset?amount={INITIAL_STOCK}")
        
        # Launch all requests simultaneously
        start_time = time.perf_counter()
        tasks = [make_purchase(session, endpoint) for _ in range(CONCURRENT_USERS)]
        results = await asyncio.gather(*tasks)
        duration = time.perf_counter() - start_time
        
        # Get final stock
        async with session.get(f"{BASE_URL}/stock") as resp:
            data = await resp.json()
            final_stock = data["current_stock"]
        
        successful = results.count(200)
        return successful, final_stock, duration


def print_report(unsafe: tuple, safe: tuple) -> None:
    """Prints a formatted comparison report."""
    u_sales, u_stock, u_time = unsafe
    s_sales, s_stock, s_time = safe
    
    u_status = "⚠️  OVERSELLING" if u_sales > INITIAL_STOCK else "✓ OK"
    s_status = "⚠️  ERROR" if s_sales != INITIAL_STOCK else "✓ PERFECT"
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🔥 FLASH SALE CONCURRENCY TEST REPORT 🔥                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Scenario: {CONCURRENT_USERS} users fighting for {INITIAL_STOCK} items                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ❌ UNSAFE METHOD (Race Condition)                                           ║
║     Successful Sales...: {u_sales:<4}                                              ║
║     Final Stock........: {u_stock:<4}                                              ║
║     Time...............: {u_time:.3f}s                                            ║
║     Status.............: {u_status:<25}                   ║
║                                                                              ║
║  ✅ SAFE METHOD (Lua Script Atomic)                                          ║
║     Successful Sales...: {s_sales:<4}                                              ║
║     Final Stock........: {s_stock:<4}                                              ║
║     Time...............: {s_time:.3f}s                                            ║
║     Status.............: {s_status:<25}                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")
    
    if u_sales > INITIAL_STOCK:
        oversold = u_sales - INITIAL_STOCK
        print(f"💀 CRITICAL: Unsafe method sold {oversold} items that didn't exist!")
        print(f"   This means {oversold} customers will receive refunds or complaints.\n")


async def main():
    print("\n🚀 Starting Flash Sale Concurrency Test...")
    print(f"   Target: {BASE_URL}")
    print(f"   Concurrent Users: {CONCURRENT_USERS}")
    print(f"   Initial Stock: {INITIAL_STOCK}\n")
    
    print("🔴 Running UNSAFE attack...")
    unsafe_results = await run_attack("unsafe")
    
    await asyncio.sleep(1)  # Brief pause between tests
    
    print("🟢 Running SAFE attack...")
    safe_results = await run_attack("safe")
    
    print_report(unsafe_results, safe_results)


if __name__ == "__main__":
    asyncio.run(main())
