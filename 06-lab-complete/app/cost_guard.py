from datetime import datetime, timezone

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import r


PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

CHARGE_BUDGET = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current + tonumber(ARGV[1]) > tonumber(ARGV[2]) then
    return 0
end
redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])
redis.call('EXPIRE', KEYS[1], 172800)
return 1
"""


def daily_key() -> str:
    return f"budget:usd:{datetime.now(timezone.utc):%Y-%m-%d}"


def check_budget() -> None:
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    try:
        current = float(r.get(daily_key()) or 0)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    if current >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (
        input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K
    ) / 1000
    if r is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    try:
        charged = r.eval(CHARGE_BUDGET, 1, daily_key(), cost, settings.daily_budget_usd)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    if not charged:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")
    return cost
