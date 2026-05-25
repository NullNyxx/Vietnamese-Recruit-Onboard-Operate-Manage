# Rate Limiting Strategy

Vroom HR implements rate limiting at multiple levels to protect the API from abuse and ensure fair usage.

## Overview

| Endpoint Type               | Limit       | Window     | Scope           |
| --------------------------- | ----------- | ---------- | --------------- |
| Login                       | 5 requests  | 60 seconds | Per IP address  |
| ESS (Employee Self-Service) | 60 requests | 60 seconds | Per employee ID |
| Gmail API                   | 5 requests  | 60 seconds | Per user        |
| Sync Operations             | Variable    | Variable   | Per operation   |

## Implementation

### Technology

- **Redis** with sorted sets for sliding window algorithm
- Stores timestamps as scores in sorted sets
- Key format: `rate_limit:<type>:<identifier>`

### Sliding Window Algorithm

```python
# Pseudocode
key = f"rate_limit:login:{ip}"
now = time.time()
window_start = now - 60  # 60 seconds

# 1. Remove expired entries
redis.zremrangebyscore(key, "-inf", window_start)

# 2. Count current requests
current_count = redis.zcard(key)

# 3. Check limit
if current_count >= 5:
    return 429

# 4. Add current request
redis.zadd(key, {str(now): now})
redis.expire(key, 60)
```

## Configuration

### Login Rate Limiting

Configured in `backend/src/modules/identity/infrastructure/config.py`:

```python
class AuthSettings(BaseSettings):
    rate_limit_login_max: int = 5          # Max requests
    rate_limit_login_window_seconds: int = 60  # Window in seconds
```

### ESS Rate Limiting

Configured in `backend/src/modules/self_service/api/rate_limiter.py`:

```python
class ESSRateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        max_requests: int = 20,
        window_seconds: int = 60,
    ) -> None:
        ...
```

### Gmail Rate Limiting

Configured in `backend/src/modules/gmail/infrastructure/config.py`:

```python
class GmailSettings(BaseSettings):
    max_retries: int = 3
    retry_backoff_base: int = 2
    max_retry_after_seconds: int = 30
```

## Response Headers

When rate limited, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 25

{
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later."
}
```

### Headers

| Header                  | Description                           |
| ----------------------- | ------------------------------------- |
| `X-RateLimit-Limit`     | Maximum requests allowed in window    |
| `X-RateLimit-Remaining` | Remaining requests in current window  |
| `X-RateLimit-Reset`     | Unix timestamp when the window resets |
| `Retry-After`           | Seconds to wait before retrying       |

## Retry-After Calculation

The `Retry-After` header is calculated based on the oldest request in the window:

```python
# Get oldest entry's timestamp
oldest_entries = await redis.zrange(key, 0, 0, withscores=True)

if oldest_entries:
    oldest_timestamp = oldest_entries[0][1]
    retry_after = ceil(oldest_timestamp + window_seconds - now)
```

Example: If the oldest request was 50 seconds ago and the window is 60 seconds, `Retry-After` will be ~10 seconds.

## Error Handling

### Rate Limit Exceeded (429)

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=429,
    detail={
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests. Please try again later.",
    },
    headers={"Retry-After": str(retry_after)},
)
```

## Testing

Run rate limiter tests:

```bash
cd backend
pytest tests/modules/self_service/test_rate_limiter.py -v
pytest tests/modules/identity/test_rate_limiter.py -v
```

### Test Cases

- ✅ Allows requests under the limit
- ✅ Blocks requests at the limit
- ✅ Blocks requests over the limit
- ✅ Returns correct Retry-After header
- ✅ Calculates Retry-After correctly
- ✅ Resets after window expires

## Monitoring

Rate limit events are logged via the standard logging system:

```python
logger.warning(
    "Rate limit exceeded for employee %s: %d requests in %d seconds",
    employee_id,
    current_count,
    window_seconds,
)
```

## Future Considerations

- Add per-endpoint rate limiting
- Add rate limit tiers (free/paid)
- Add rate limit dashboard in admin panel
- Consider using API gateways (Kong, Traefik) for centralized rate limiting
