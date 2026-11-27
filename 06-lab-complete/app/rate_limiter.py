from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import r


WINDOW_SECONDS = 60
SLIDING_WINDOW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
local window_ms = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])

redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window_ms)
if redis.call('ZCARD', KEYS[1]) >= limit then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    if #oldest == 0 then
        return math.ceil(window_ms / 1000)
    end
    return math.max(1, math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000))
end

redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window_ms)
return 0
"""


def check_rate_limit(key: str) -> None:
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    key_hash = sha256(key.encode()).hexdigest()
    try:
        retry_after = r.eval(
            SLIDING_WINDOW, 1, f"rate:{key_hash}", WINDOW_SECONDS * 1000,
            settings.rate_limit_per_minute, uuid4().hex,
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
