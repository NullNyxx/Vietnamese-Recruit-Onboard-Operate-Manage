# Caching Strategy

Vroom HR uses Redis for rate limiting and selected cache-backed workflows.
Attendance and leave-balance caching described below is retired in the current
backend after migration `027_drop_attendance_payroll_tables.py`; keep it as
reference material only until attendance is reintroduced.

## Overview

| Data          | Cache Key                            | TTL              | Invalidation             |
| ------------- | ------------------------------------ | ---------------- | ------------------------ |
| Leave Balance | `leave_balance:{employee_id}:{year}` | 5 minutes (300s) | On submit/approve/reject |

## Retired Implementation Reference

### Leave Balance Cache

Employee leave balance caching belonged to the retired attendance module:

**Location**: `backend/src/modules/attendance/application/balance_service.py`

```python
# Cache key format
CACHE_KEY_PREFIX = "leave_balance"
CACHE_TTL_SECONDS = 300  # 5 minutes

def _make_cache_key(employee_id: UUID, year: int) -> str:
    """Generate cache key for leave balance."""
    return f"{CACHE_KEY_PREFIX}:{employee_id}:{year}"
```

### Cache Invalidation

Leave balance cache is invalidated when:

1. **Employee submits a leave request**

   ```python
   await invalidate_leave_balance(employee_id, year)
   ```

2. **Leave request status changes** (approve/reject)

   ```python
   await invalidate_leave_balance(employee_id, year)
   ```

3. **Leave balance is manually updated**
   ```python
   await invalidate_leave_balance(employee_id, year)
   ```

### Cache Implementation

```python
class LeaveBalanceCache:
    """Redis cache for leave balances."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._ttl = 300  # 5 minutes

    async def get(self, employee_id: UUID, year: int) -> LeaveBalance | None:
        """Get cached leave balance."""
        key = f"leave_balance:{employee_id}:{year}"
        data = await self._redis.get(key)
        if data:
            return LeaveBalance.model_validate_json(data)
        return None

    async def set(
        self,
        employee_id: UUID,
        year: int,
        balance: LeaveBalance,
    ) -> None:
        """Cache leave balance."""
        key = f"leave_balance:{employee_id}:{year}"
        await self._redis.setex(key, self._ttl, balance.model_dump_json())

    async def invalidate(self, employee_id: UUID, year: int) -> None:
        """Invalidate cached leave balance."""
        key = f"leave_balance:{employee_id}:{year}"
        await self._redis.delete(key)
```

## Configuration

Cache settings are configured via environment variables:

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional
```

## Redis Keys Pattern

| Pattern              | Description                 | TTL     |
| -------------------- | --------------------------- | ------- |
| `rate_limit:login:*` | Login rate limit per IP     | 60s     |
| `rate_limit:ess:*`   | Retired ESS rate limit per employee | 60s     |
| `leave_balance:*`    | Retired employee leave balances     | 300s    |
| `oauth:token:*`      | Encrypted OAuth tokens      | Session |
| `whitelist:*`        | Email whitelist cache       | 3600s   |

## Best Practices

### 1. Cache Invalidation

Always invalidate cache when underlying data changes:

```python
async def update_leave_balance(employee_id: UUID, year: int):
    # Update database
    await repository.update_balance(...)

    # Invalidate cache
    await cache.invalidate(employee_id, year)
```

### 2. Cache-Aside Pattern

```
1. Check cache
2. If miss → fetch from DB
3. Store in cache
4. Return data
```

### 3. TTL Selection

- **Short TTL (1-5 min)**: Data that changes frequently
- **Medium TTL (15-30 min)**: Semi-static data
- **Long TTL (1-24 hours)**: Static reference data

### 4. Monitoring

Monitor cache hit rates:

```python
# Log cache hits/misses
logger.info(
    "Cache %s for key=%s",
    "hit" if cached else "miss",
    cache_key,
)
```

## Future Caching Opportunities

Consider adding cache for:

1. **Employee lists** — Cache list of employees per department
2. **Department/Position reference data** — Rarely changes
3. **Payslip generation** — Heavy computation, cache per period
4. **Candidate pipeline stats** — Aggregated metrics

## Testing

```bash
# Test Redis connection
redis-cli ping
# PONG

# Monitor cache keys
redis-cli keys "leave_balance:*"

# Check TTL
redis-cli ttl leave_balance:123e4567-e89b-12d3-a456-426614174000:2025
```

## Health Check

```python
@app.get("/health/cache")
async def cache_health():
    """Check Redis connectivity."""
    try:
        await redis.ping()
        return {"status": "ok", "cache": "connected"}
    except Exception as e:
        return {"status": "error", "cache": "disconnected", "error": str(e)}
```
