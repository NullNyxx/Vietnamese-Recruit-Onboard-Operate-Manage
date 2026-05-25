# Logging & Monitoring

Vroom HR implements structured logging for observability and debugging.

## Logging

### Implementation

All modules use a centralized logger from `backend/src/modules/common/logger.py`:

```python
from src.modules.common.logger import logger

logger.info("Employee created", extra={"employee_id": str(employee.id)})
```

### Structure

Each log entry includes:

- `timestamp` — ISO 8601 format
- `level` — DEBUG, INFO, WARNING, ERROR, CRITICAL
- `message` — Human-readable message
- `request_id` — Unique request identifier (if available)
- `module` — Source module name

### Request Logging

All HTTP requests are logged with structured data:

```json
{
  "timestamp": "2025-05-25T10:30:00.000Z",
  "request_id": "req-abc123",
  "method": "POST",
  "path": "/api/v1/employees",
  "status_code": 201,
  "duration_ms": 145,
  "user_id": "user-123"
}
```

### Log Levels

| Level    | Usage                                        |
| -------- | -------------------------------------------- |
| DEBUG    | Detailed debugging info (queries, variables) |
| INFO     | Normal operations (requests, user actions)   |
| WARNING  | Unexpected but handled (validation errors)   |
| ERROR    | Failures that need attention (exceptions)    |
| CRITICAL | System-wide failures                         |

### Module-Specific Logging

Each module logs relevant information:

**Identity Module**

```python
logger.info("User login successful", extra={"email": email, "ip": ip})
logger.warning("Login failed - invalid credentials", extra={"email": email})
logger.warning("Rate limit exceeded", extra={"ip": ip, "attempts": count})
```

**Attendance Module**

```python
logger.info("Check-in recorded", extra={"employee_id": eid, "time": check_in_time})
logger.info("Leave request submitted", extra={"employee_id": eid, "type": leave_type})
```

**ESS Audit Log**

```python
logger.info(
    "ESS action performed",
    extra={
        "employee_id": employee_id,
        "action": "view_payslip",
        "resource_id": payslip_id,
    }
)
```

### Configuration

Logging is configured in `backend/src/main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

For production, use structured JSON logging:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_data)
```

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health
# {"status": "ok"}
```

### Prometheus Metrics (Future)

Consider adding Prometheus metrics for:

- Request duration histogram
- Request count by endpoint
- Error rate by type
- Active users
- Database connection pool usage

Example:

```python
from prometheus_client import Counter, Histogram

request_duration = Histogram(
    'http_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint', 'status']
)

request_count = Counter(
    'http_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)
```

### Log Aggregation

For production, consider:

| Tool      | Purpose                    |
| --------- | -------------------------- |
| ELK Stack | Centralized logging        |
| Loki      | Grafana-compatible logging |
| Datadog   | APM + Logging              |
| Sentry    | Error tracking             |

### Application Performance

Key metrics to monitor:

1. **Response Time**
   - p50, p95, p99 latency
   - By endpoint

2. **Error Rate**
   - 5xx errors per minute
   - By endpoint and error type

3. **Resource Usage**
   - CPU, Memory
   - Database connections
   - Redis connections

4. **Business Metrics**
   - Active users
   - Leave requests submitted
   - Payroll processing time

## Structured Logging Best Practices

### DO

```python
# ✅ Use structured logging with extra fields
logger.info("Employee created", extra={
    "employee_id": str(employee.id),
    "department": employee.department.name,
    "action": "create"
})

# ✅ Include request ID for tracing
logger.info("Request processed", extra={
    "request_id": request.state.request_id,
    "duration_ms": duration
})

# ✅ Log errors with context
logger.error("Failed to send email", extra={
    "employee_id": employee_id,
    "error": str(e),
    "template": "welcome"
})
```

### DON'T

```python
# ❌ Don't use f-strings in logging
logger.info(f"Employee {employee.id} created")  # Bad

# ❌ Don't log sensitive data
logger.info(f"User password: {password}")  # Very bad!

# ❌ Don't log without context
logger.info("Something happened")  # Unhelpful
```

## Debugging Tips

### View Logs in Development

```bash
# All logs
uvicorn src.main:app --reload --log-level info

# Debug mode
uvicorn src.main:app --reload --log-level debug
```

### Query Logs

```bash
# Find all requests for a specific user
grep "user_id.*123" application.log

# Find all errors in the last hour
grep "ERROR" application.log | grep "2025-05-25"

# Find slow requests
grep "duration_ms.*1000" application.log
```

## Future Enhancements

1. **Distributed Tracing** — Add OpenTelemetry for request tracing across services
2. **Metric Dashboard** — Grafana dashboard for key metrics
3. **Alerting** — Alert on error rate spikes
4. **Log Retention** — Define retention policy (30 days dev, 1 year prod)
