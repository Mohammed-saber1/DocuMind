import asyncio
from typing import TypeVar, Any

T = TypeVar("T")

async def async_timeout_wrapper(coro: Any, timeout: float, operation_name: str) -> T | None:
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"timeout: {operation_name}")
        return None
    except Exception as e:
        print(f"error: {operation_name}, {e}")
        return None
