# Architecture Decisions Record (ADR)

This document records key technical decisions, trade-offs, and scaling roadmaps for the SmartDialer platform.

---

## 1. Why FastAPI Was Selected

### Context
Contact-center telephony requires high throughput, minimal overhead, asynchronous event ingestion, and automatic API schema validation.

### Decision
FastAPI was chosen because:
1. **Asynchronous & High-Performance**: Built on Starlette and Pydantic, providing native ASGI concurrency capable of processing thousands of provider webhooks concurrently.
2. **Deterministic Data Validation**: Pydantic v2 schemas enforce strict input sanitization, phone number format checks, and status validation at runtime.
3. **Interactive Documentation**: Automatic OpenAPI 3.0 (Swagger UI at `/docs` and ReDoc at `/redoc`) enables developers and integration engineers to inspect and test all routes immediately without external tooling.
4. **Clean Dependency Injection**: Modular session lifecycle management (`Depends(get_db)`) simplifies in-memory testing and connection pooling.

---

## 2. Why SQLite Was Selected for Prototype

### Context
Recruitment assignment evaluation requires a standalone, runnable setup that runs out-of-the-box without requiring external database provisioning (Docker, PostgreSQL, MySQL).

### Decision
SQLite with Write-Ahead Logging (WAL) was selected:
- **Zero Configuration**: No external daemon, port conflicts, or connection credential management.
- **WAL Mode Optimization**: By executing `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`, SQLite supports concurrent readers alongside a concurrent writer without database lock collisions.
- **Testing Agility**: In-memory execution (`sqlite://` with `StaticPool`) enables 14 comprehensive unit tests to run and pass in under 1 second.

---

## 3. How Concurrency Is Controlled

### Problem
In multi-worker environments, two progressive dialer workers might simultaneously inspect the queue, pick the same `AVAILABLE` agent, and attempt to dial two concurrent calls bound to the same agent.

### Solution
1. **Atomic Conditional Updates**:
   Allocation does not rely on frontend checks or naive Python state inspections. Instead, an atomic SQL conditional statement is executed:
   ```sql
   UPDATE agents 
   SET status = 'RESERVED', reserved_at = :now 
   WHERE id = :agent_id AND status = 'AVAILABLE';
   ```
   If another worker already updated the agent, `result.rowcount` is 0. The transaction safely rolls back and retries with the next candidate.
2. **Borrower Double-Allocation Prevention**:
   The exact same pattern protects the borrower queue:
   ```sql
   UPDATE borrowers 
   SET call_status = 'CALLING', attempt_count = attempt_count + 1 
   WHERE id = :borrower_id AND call_status = 'UNPROCESSED';
   ```
3. **Application Reentrant Mutex**:
   An application-level `threading.RLock` (`_allocation_lock`) serializes the fast memory-to-SQL pairing step across worker threads.

---

## 4. How Idempotency Works

### Problem
Telephony providers frequently retry webhook delivery if an acknowledgment packet is delayed. Network retries can cause duplicate `ANSWERED`, `RINGING`, or `COMPLETED` signals to arrive multiple times.

### Solution
1. **Unique Provider Event IDs**:
   Every incoming provider event payload must supply an `event_id`.
2. **Audit Table De-Duplication**:
   The `provider_events` table enforces a `UNIQUE(event_id)` index.
3. **Idempotent Acknowledgment**:
   When a duplicate event arrives, the system detects the existing record, writes no new state changes to the `calls` table, and returns `HTTP 200 OK` with status `IGNORED_DUPLICATE`.
4. **Terminal State Lock**:
   Calls in `COMPLETED`, `FAILED`, or `CANCELLED` cannot transition back to an active state under any circumstances, preventing late duplicate events from reopening completed sessions.

---

## 5. How Failures Are Recovered

| Failure Mode | Impact | Recovery Mechanism |
| :--- | :--- | :--- |
| **Worker Process Crash** | Agent stuck in `RESERVED` status | Background Sweeper (`recover_stale_reservations`) detects reservations older than 45s with no active call and resets agent to `AVAILABLE`. |
| **Telecom Circuit Error (503)** | Gateway rejected dial command | Call allocator catches failure, marks Call `FAILED`, and immediately releases agent to `AVAILABLE`. |
| **Gateway Timeout (504)** | Gateway unresponsive | Gateway returns timeout; call is transitioned to `FAILED`; agent is restored to `AVAILABLE`. |
| **Out-of-Order Webhook** | Late signal received out of sequence | Event sequence rank check flags event as `IGNORED_OUT_OF_ORDER`. Call remains in its advanced state. |
| **Carrier Outage** | Telecom trunk down | Safety Controller halts all outbound dialing immediately (`PROVIDER_OUTAGE_SHUTDOWN`). |

---

## 6. What Would Change for Production Scale

While this prototype architecture is fully self-contained, a large-scale enterprise deployment handling millions of calls daily would incorporate:

1. **PostgreSQL with Row-Level Locking**:
   Replace SQLite with PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED` for concurrent worker queue consumption without lock contention.
2. **Distributed Telemetry & Cache (Redis)**:
   Store ephemeral agent presence (`AVAILABLE`, `RESERVED`) in Redis with TTLs (Time-To-Live) and Redlock distributed locks.
3. **Distributed Task Queue (Celery / Kafka)**:
   Decouple pacing calculation from call dispatch via a high-throughput event streaming broker (Apache Kafka or AWS SQS + Celery).
4. **Real-Time Telephony Gateways**:
   Replace mock providers with real SIP trunks (Twilio Voice API, Amazon Connect, Asterisk/FreeSWITCH PBX) using WebRTC audio bridges for agent softphones.
5. **Circuit Breaker Pattern**:
   Implement standard Netflix Hystrix / Resilience4j style circuit breakers on gateway endpoints to automatically trip from closed to open when 5xx errors exceed 5% over a 1-minute window.
