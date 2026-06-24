import json
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis_pool


async def cache_get(key: str):
    r = await get_redis()
    value = await r.get(key)
    return json.loads(value) if value else None


async def cache_set(key: str, value, ttl: int | None = None):
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ttl or settings.redis_ttl)


async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)
