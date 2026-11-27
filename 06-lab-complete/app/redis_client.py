from redis import Redis
from redis.exceptions import RedisError

from app.config import settings


r = (
    Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    if settings.redis_url
    else None
)


def redis_healthy() -> bool:
    if r is None:
        return False

    try:
        return bool(r.ping())
    except RedisError:
        return False
