import os, time, json, redis
from typing import Any

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
rds = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def rate_limit(bucket_key: str, limit_per_min: int = 60):
    now_min = int(time.time() // 60)
    key = f"rl:{bucket_key}:{now_min}"
    cnt = rds.incr(key)
    if cnt == 1:
        rds.expire(key, 65)
    if cnt > limit_per_min:
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

def get_idempotent(key: str):
    v = rds.get(f"idemp:{key}")
    return json.loads(v) if v else None

def set_idempotent(key: str, value: Any, ttl_seconds: int = 600):
    rds.setex(f"idemp:{key}", ttl_seconds, json.dumps(value, ensure_ascii=False))
