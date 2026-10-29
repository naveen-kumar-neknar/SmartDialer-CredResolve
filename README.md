# SmartDialer | Telephony Progressive & Predictive Dialer Platform

SmartDialer is a full-stack, enterprise-grade outbound dialing management platform built for contact centers and financial operations. It integrates progressive and predictive dialing algorithms with an autonomous **Safety Controller** to eliminate dropped borrower calls and guarantee zero overdial abandonment.

---

## Key Highlights

- **Zero Abandoned Calls Guarantee**: Sits between predictive recommendations and telephony execution to enforce mathematical capacity limits and progressive fallback.
- **Progressive Dialer**: 1:1 atomic agent-borrower pairing protected by database-level conditional transactions.
- **Explainable Predictive Pacing Engine**: Rule-based algorithm balancing idle capacity, active turnover, in-flight ringing calls, answer rates, and provider health.
- **Dual Telecom Providers**:
  - **Provider A**: Tier-1 telecom trunk (low latency, >98% reliability).
  - **Provider B**: Volatile trunk simulating carrier errors (503), timeouts (504), duplicate webhooks, and out-of-order events.
- **Idempotent Webhook Processing**: Unique event tracking, out-of-order sequence detection, and terminal state protection.
- **Modern Fintech Dashboard**: Real-time React 18 + Vite frontend with dark-mode aesthetic, interactive pacing simulator, and audit logs.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite (WAL mode), Pydantic v2, Pytest |
| **Frontend** | React 18, Vite 5, JavaScript, CSS3 (Custom Fintech Design System), Lucide Icons |
| **Simulation** | Standalone Python Simulation Benchmark Suite |

---

## Project Structure

```
SmartDialer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entrypoint & middleware
│   │   ├── database.py          # SQLAlchemy engine & SQLite WAL config
│   │   ├── models/              # Agent, Borrower, Call, Event, Safety models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # Domain endpoints (agents, borrowers, calls, dialer, safety, providers, demo)
│   │   └── services/            # CallAllocator, PacingEngine, SafetyController, EventProcessor, Providers
│   ├── tests/
│   │   ├── conftest.py          # Pytest in-memory database & client fixtures
│   │   └── test_dialer.py       # 14 comprehensive unit & integration tests
│   ├── pytest.ini               # Test configuration
│   └── requirements.txt         # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/          # Sidebar, Header, MetricCards, CallsTable, AgentsTable, etc.
│   │   ├── api.js               # Centralized REST API client
│   │   ├── App.jsx              # Main dashboard application
│   │   ├── index.css            # Polished fintech CSS design system
│   │   └── main.jsx             # React entrypoint
│   ├── index.html               # Web application shell
│   ├── package.json             # NPM package manifest
│   └── vite.config.js           # Vite dev server & API proxy config
├── simulation/
│   └── run_simulation.py        # Telephony benchmark engine (Scenarios A, B, C, D)
├── docs/
│   ├── architecture.md          # Architecture overview & Mermaid diagrams
│   ├── agent-state-machine.md   # Agent state machine transitions
│   ├── call-state-machine.md    # Call state machine & terminal protection
│   └── architecture-decisions.md# Architectural decisions (ADRs) & production scaling
├── .gitignore                   # Git exclusions
└── README.md                    # Platform documentation
```

---

## Prerequisites

- **Python**: Version 3.10+ (Tested on Python 3.12)
- **Node.js**: Version 18+ (Tested on Node v24)
- **npm**: Version 9+

---

## Backend Installation & Setup

1. **Navigate to the backend directory**:
   ```bash
   cd SmartDialer/backend
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the backend development server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Verify API health**:
   - Health endpoint: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - Interactive Swagger API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Frontend Installation & Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd SmartDialer/frontend
   ```

2. **Install dependencies** (ultra-lightweight, takes ~5 seconds):
   ```bash
   npm install
   ```

3. **Run the Vite development server**:
   ```bash
   npm run dev
   ```
   *Dashboard opens at: [http://localhost:5173](http://localhost:5173)*

4. **Default Authentication Credentials**:
   - **Supervisor**: `supervisor@credresolve.com` | Password: `credresolve123`
   - **Agent**: `agent@credresolve.com` | Password: `credresolve123`
   *(1-Click Demo buttons are also available directly on the login screen).*

5. **Production Build & Preview** (Optional):
   ```bash
   npm run build
   npm run preview
   ```
   *Note: Pre-built production distribution files are also included in `frontend/dist/`.*

---

## Running Automated Tests

Execute the 20 comprehensive unit, concurrency, security, and safety tests:

```bash
cd SmartDialer/backend
pytest tests -v
```

### Verified Test Suite (20 Tests, 100% Pass Rate):
- `test_health_endpoint`: Verifies API gateway status check.
- `test_agent_creation_and_state_transitions`: Validates agent state machine rules.
- `test_borrower_creation_and_pii_masking`: Verifies phone number masking to ensure zero real PII.
- `test_successful_progressive_dialing`: Validates 1:1 agent/borrower progressive allocation.
- `test_no_available_agent`: Ensures dialer halts safely when capacity is 0.
- `test_concurrent_allocation_attempts`: ThreadPool test proving zero duplicate allocations under concurrent load.
- `test_duplicate_provider_events`: Proves webhook idempotency and duplicate event rejection.
- `test_out_of_order_provider_events`: Proves late events cannot move connected calls backward.
- `test_terminal_call_protection`: Proves completed calls cannot be reopened by late events.
- `test_provider_timeout_handling`: Verifies automatic rollback of agent reservations on gateway timeout.
- `test_provider_outage_stops_dialing`: Verifies immediate dialing halt during provider outages.
- `test_safety_controller_limits_and_decisions`: Tests capacity reduction and rule audits.
- `test_predictive_pacing_different_answer_rates`: Tests pacing formula at 20%, 50%, and 70% answer rates.
- `test_reservation_expiry_and_recovery`: Verifies background recovery of stale reservations after worker crash.
- `test_concurrent_borrower_allocation`: Verifies atomic single-borrower allocation under concurrent load.
- `test_failed_call_simulation_releases_resources`: Verifies agent and borrower release on call failure.
- `test_sudden_agent_drop_reflected_in_safety_decisions`: Verifies safety controller adaptation to agent shortage.
- `test_invalid_call_state_transitions_rejected`: Verifies state machine boundary rejection.
- `test_auth_signup_and_login`: Verifies user registration, password verification, and session token generation.
- `test_auth_invalid_credentials`: Verifies 401 Unauthorized rejection on incorrect passwords.

---

## Running Telephony Simulations

Run the standalone benchmark across Scenarios A, B, C, and D:

```bash
python simulation/run_simulation.py
```

### Simulation Scenarios:
- **Scenario A**: 20% answer rate, 120s average talk time
- **Scenario B**: 50% answer rate, 90s average talk time
- **Scenario C**: 70% answer rate, 180s average talk time
- **Scenario D**: Variable answer rate (20-80%), latency spikes, and Provider B carrier failures

**Result**: 0 abandoned calls across all scenarios while maintaining 76%–96% agent fleet utilization.

---

## REST API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | API gateway health check |
| `GET` | `/api/dashboard/stats` | Live KPI metrics (agents, calls, connection & utilization rates) |
| `GET` | `/api/agents` | List all agents |
| `POST` | `/api/agents` | Create a new agent |
| `PATCH` | `/api/agents/{id}/status` | Safely update agent status with transition validation |
| `GET` | `/api/borrowers` | List borrowers ordered by tier priority |
| `POST` | `/api/borrowers` | Create a borrower with masked phone number |
| `GET` | `/api/calls` | List recent call sessions |
| `GET` | `/api/calls/{id}` | Inspect call details with borrower and agent metadata |
| `POST` | `/api/calls/initiate` | Initiate a single progressive call allocation |
| `POST` | `/api/calls/{id}/simulate` | Simulate call progression (`CONNECTED`, `COMPLETED`, `FAILED`) |
| `POST` | `/api/dialer/progressive` | Dispatch a safe progressive dialing batch |
| `POST` | `/api/dialer/predictive/simulate`| Calculate predictive pacing proposal & safety review |
| `GET` | `/api/safety/decisions` | Audit history of Safety Controller verdicts |
| `GET` | `/api/providers/health` | Telecom gateway health and failure telemetry |
| `POST` | `/api/providers/config` | Switch active provider (A/B) and configure chaos parameters |
| `POST` | `/api/providers/outage` | Toggle simulated total provider outage |
| `POST` | `/api/providers/events/webhook` | Ingest telephony webhook event with idempotency check |
| `POST` | `/api/demo/seed` | Seed 6 fictional agents and 25 fictional borrowers |
| `POST` | `/api/recovery/run` | Reclaim stale agent & borrower reservations |

---

## Example Workflow

1. **Seed Fictional Data**: Click **Seed Demo Data** on the dashboard (or POST `/api/demo/seed`). This populates 6 fictional agents and 25 fictional borrowers with masked phone numbers.
2. **Start Progressive Batch**: On the Overview or Dialer tab, click **Dial 1 Progressive Call**. The allocator pairs an `AVAILABLE` agent with a Tier 1 borrower, locks their state, and dispatches the call through the active gateway.
3. **Simulate Call Progression**: On the Call Log, click **Connect** to simulate the borrower answering, then **Complete** to simulate call conclusion. Observe the agent transitioning to `WRAP_UP` and returning to `AVAILABLE`.
4. **Test Predictive Pacing**: Navigate to **Dialer & Pacing**, adjust the answer rate slider, and click **Simulate Pacing Proposal**. Inspect the Safety Controller verdict, approved dials, and mathematical explanation.
5. **Test Telecom Chaos**: Navigate to **Telecom Providers**, switch to **Provider B**, toggle carrier circuit failure or duplicate events, and verify that the Safety Controller throttles capacity and deduplicates events.

---

## Known Limitations

- **Local Telephony Mock**: Real telephone networks require external SIP trunks (Twilio / Amazon Connect). This platform emulates provider protocols using in-process gateways.
- **SQLite Single-Writer Concurrency**: Optimized using WAL mode and row-level conditional updates for prototype scale; enterprise production would use PostgreSQL `SKIP LOCKED` and Redis distributed locks (detailed in `docs/architecture-decisions.md`).
