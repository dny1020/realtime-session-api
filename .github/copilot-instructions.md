# Repository custom instructions for Copilot

Purpose
- This repository exposes a minimal Python FastAPI service to trigger single outbound IVR calls via Asterisk ARI and to query their status; no predictive or campaign-style dialing is in scope. Focus on per-number call origination and status queries only.
- Primary endpoints:
  - POST /api/v1/interaction/{number}: Initiate a call to a specific number (connect to IVR context or play audio).
  - GET /api/v1/status/{call_id}: Retrieve call status (pending, ringing, answered, failed).
  - RESTful alternatives:
    - POST /api/v1/calls: Create a call by body payload.
    - GET /api/v1/calls/{call_id}: Get call details/status.

Tech stack and components
- Language/runtime: Python 3.x; framework: FastAPI; persistence: PostgreSQL via SQLAlchemy (production) with optional DB-disabled mode for local dev; telephony control: Asterisk ARI (HTTP/WebSocket).
- Packaging/deploy: Docker optional; reverse proxy: Traefik optional; metrics: Prometheus (scrapes /metrics when enabled), dashboards: Grafana (not exposed by default).
- Authentication: OAuth2 Password Grant for JWT at POST /api/v1/token; tokens carry sub, iat, exp, optionally iss/aud; passwords stored hashed (bcrypt).

Scope and non-goals
- In-scope: Single-call origination via Asterisk ARI, basic IVR/audio playback, call status tracking/queries, minimal persistence for calls (production).
- Out-of-scope: Campaign management, predictive dialing, inbound call flows, multi-tenant features, advanced IVR designers, exposing Asterisk ARI publicly.

Project layout
- app/main.py: FastAPI entrypoint.
- app/routes/: Routers and controllers for endpoints.
- app/services/: Business logic for Asterisk ARI origination and status tracking.
- app/models/: ORM and pydantic schemas.
- config/settings.py: Env-var backed configuration (pydantic settings).
- Dockerfile, requirements.txt, README.md at repo root.

Architecture expectations
- FastAPI serves REST endpoints and exposes /docs and /metrics (only when enabled). Asterisk is accessed internally via ARI over HTTP/WebSocket. PostgreSQL persists calls in production. Traefik may front the API in deployments. Prometheus scrapes metrics. Grafana reads from Prometheus. Do not introduce external public exposure for Asterisk ARI.

Configuration and environment
- Database:
  - DATABASE_URL required for production runs.
  - DISABLE_DB=true enables minimal mode (no DB) for local dev/testing; note: token endpoint requires DB.
- Asterisk ARI:
  - ARI_HTTP_URL, ARI_USERNAME, ARI_PASSWORD, ARI_APP must be set; the API connects internally; do not expose ARI publicly.
- Call defaults:
  - DEFAULT_CONTEXT, DEFAULT_EXTENSION, DEFAULT_PRIORITY, DEFAULT_TIMEOUT, DEFAULT_CALLER_ID used when not provided per request.
- Auth and security:
  - SECRET_KEY is mandatory; optional JWT_ISSUER, JWT_AUDIENCE for token claims.
- Metrics:
  - METRICS_ENABLED toggles /metrics; ensure low-cardinality labels.

Build, run, and validate
- Local (minimal mode):
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
  - export DISABLE_DB=true
  - Ensure Asterisk with ARI is reachable (proper ARI_* env vars set).
  - uvicorn app.main:app --reload
- Production (with DB):
  - Ensure DATABASE_URL, SECRET_KEY, ARI_* vars are set; DISABLE_DB not set or false.
  - Run via uvicorn or container entrypoint; front with a reverse proxy (e.g., Traefik) with HTTPS.
- Validation steps the agent should rely on:
  - Token retrieval at POST /api/v1/token succeeds only when DB is enabled and users exist with hashed passwords.
  - Protected endpoints require Authorization: Bearer <token>.
  - /metrics is reachable only when METRICS_ENABLED=true; avoid leaking high-cardinality labels.

API contracts (behavior Copilot must preserve)
- POST /api/v1/interaction/{number}
  - Body fields: context, extension, priority, timeout, caller_id (defaults apply if missing).
  - Response includes: success, call_id (UUID), phone_number, message, channel, status (e.g., dialing), created_at.
- GET /api/v1/status/{call_id}
  - Response includes: call_id, phone_number, status, channel, context, extension, caller_id, timestamps (created_at, dialed_at, answered_at, ended_at), duration, failure_reason, attempt_number, is_active, is_completed.
- RESTful alternatives remain consistent with above behaviors and schemas.

Coding conventions
- Prefer async FastAPI path handlers; use type hints everywhere. Use pydantic models for request/response validation. Centralize ARI interactions in app/services/. Keep controller logic thin and service logic cohesive.
- When DISABLE_DB=true, implement in-memory or no-op adapters for persistence boundaries so routes still function without DB (except token issuance). When DB is enabled, use SQLAlchemy models with minimal schema for call records and status transitions.
- Include structured logging for key operations (origination request, ARI events, status transitions) without leaking secrets (never log ARI credentials, JWTs, or SECRET_KEY).

Security rules
- Always require JWT on protected endpoints, validate exp/iat and optionally iss/aud. Store passwords hashed (bcrypt). Do not expose ARI or admin dashboards publicly. In production, restrict /docs and /metrics via proxy-layer auth or IP allowlists. Enforce HTTPS at the proxy.

Observability
- Expose Prometheus metrics only when METRICS_ENABLED; keep labels low-cardinality (no per-ID labels). Add basic counters/gauges for call attempts, active calls, successful/failed calls, ARI errors.

Common change points for Copilot
- Add/modify endpoints: app/routes/ with pydantic schemas in app/models/ and business logic in app/services/.
- Add configuration: config/settings.py and read via environment variables; keep defaults sensible for dev.
- Extend persistence: SQLAlchemy models in app/models/ and migrations as needed (avoid when DISABLE_DB=true).
- ARI logic: encapsulate ARI REST/WebSocket flows in app/services/ and avoid blocking I/O in handlers.

Guardrails for suggestions
- Do not add features related to campaigns, predictive dialing, inbound flows, or public ARI exposure.
- Keep endpoints minimal and consistent with documented responses. Do not introduce multi-tenant or multi-account constructs unless explicitly requested.
- Respect DISABLE_DB mode and avoid breaking token issuance assumptions (token endpoint requires DB).

Quick examples Copilot can rely on (for tests and docs)
- JWT token:
  - POST /api/v1/token with application/x-www-form-urlencoded: username, password; returns access_token and token_type.
- Originate single call:
  - POST /api/v1/interaction/+1234567890 with JSON body including context, extension, priority, timeout, caller_id; returns success, call_id, status=dialing, channel.
- Check status:
  - GET /api/v1/status/{call_id}; returns status fields and timestamps as available.

Acceptance checklist before proposing changes
- Code compiles, server starts locally with DISABLE_DB=true and ARI configured.
- Protected endpoints enforce JWT; token flow works only with DB enabled.
- No secrets or ARI endpoints exposed in logs or public routes. /metrics gated by METRICS_ENABLED.
- Responses match documented shapes and fields; no high-cardinality metrics.

