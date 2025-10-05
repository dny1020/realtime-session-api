# Contact Center API - Project Analysis

## Overview
This is a **minimal Python FastAPI service** for triggering single outbound IVR calls via Asterisk ARI. The project focuses exclusively on **per-number call origination** and **status queries**, with no predictive dialing or campaign management features.

## Project Statistics
- **Language**: Python 3.x
- **Framework**: FastAPI
- **Total Python Files**: 24 (excluding venv)
- **Application Code**: ~1,165 lines of code
- **Test Files**: 4 files, 316 total lines

## Architecture

### Core Components

#### 1. **FastAPI Application** (`app/main.py`)
- **Entry Point**: Main application with lifespan management
- **Middleware Stack**:
  - CORS middleware for cross-origin requests
  - JSON logging middleware for structured logs
  - Request ID middleware (adds X-Request-ID to responses)
  - Simple rate limiting middleware (in-memory, 10 req/60s for `/api/v2/token`)
- **Health Checks**: `/health` endpoint validates DB and Asterisk connectivity
- **Metrics**: Prometheus `/metrics` endpoint (toggleable via `METRICS_ENABLED`)
- **Security**: 
  - Validates `SECRET_KEY` is not a placeholder in production
  - Non-root user in Docker (appuser, UID 1000)

#### 2. **Asterisk ARI Integration** (`app/services/asterisk.py`)
- **Connection Management**: HTTP-based ARI client using `httpx.AsyncClient`
- **Call Origination**: 
  - Creates channels via `POST /channels` with `Local/{number}@{context}` endpoint
  - Supports custom context, extension, priority, timeout, caller_id
  - Retry logic: 3 attempts with exponential backoff (0.3s, 0.6s, 1.2s)
  - Connection pooling: configurable max keepalive (20) and max connections (50)
- **Status**: Lightweight connectivity check via `GET /applications`

#### 3. **Database Layer** (`app/database.py`, `app/models/`)
- **ORM**: SQLAlchemy with PostgreSQL
- **Dual Mode**:
  - **Production**: Full DB persistence for calls and users
  - **Development**: `DISABLE_DB=true` for minimal mode (no DB required, but token endpoint won't work)
- **Models**:
  - **Call** (`app/models/call.py`): Tracks call lifecycle with statuses (pending, dialing, ringing, answered, busy, no_answer, failed, completed)
  - **User** (`app/models/user.py`): User authentication with bcrypt-hashed passwords
- **Migrations**: Alembic for schema management (1 baseline migration present)
- **Constraints**: Phone number length (7-20 chars), attempt numbers ≥1, timeout >0

#### 4. **Authentication** (`app/auth/jwt.py`, `app/routes/auth.py`)
- **OAuth2 Password Grant**: `POST /api/v2/token` with username/password
- **JWT Tokens**: 
  - Claims: `sub` (username), `iat`, `exp`, optional `iss`/`aud`
  - Algorithm: HS256
  - Expiration: 30 minutes (configurable)
- **Password Hashing**: bcrypt via passlib
- **Protection**: All endpoints (except `/token`, `/docs`, `/health`, `/metrics`) require Bearer token

#### 5. **Metrics & Monitoring** (`app/instrumentation/metrics.py`)
- **Prometheus Metrics**:
  - **Legacy** (with double `_total` suffix - deprecated): `calls_launched_total`, `calls_success_total`, `calls_failed_total`, `calls_total`
  - **V2** (preferred): `calls_launched`, `calls_success`, `calls_failed`, `calls` (exported as `calls_*_total`)
  - **Latency**: `originate_latency_seconds` (histogram), `api_request_latency_seconds`
  - **API Requests**: `api_requests_total` (by method, path, status)
- **Grafana**: Dashboard provisioning support (not exposed by default)

### API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| **POST** | `/api/v2/token` | Issue JWT token | No |
| **POST** | `/api/v2/interaction/{number}` | Originate call to number | Yes |
| **GET** | `/api/v2/status/{call_id}` | Query call status | Yes |
| **GET** | `/api/v2/interaction/{call_id}/status` | Alias for status query | Yes |
| **POST** | `/api/v2/calls` | RESTful: Create call (body payload) | Yes |
| **GET** | `/api/v2/calls/{call_id}` | RESTful: Get call details | Yes |
| **GET** | `/` | Root info | No |
| **GET** | `/health` | Health check (DB + Asterisk) | No |
| **GET** | `/metrics` | Prometheus metrics | No (but toggleable) |
| **GET** | `/docs` | OpenAPI/Swagger UI | No (toggleable) |

### Request/Response Flow

```
Client → Traefik (HTTPS) → FastAPI (JWT validation) → AsteriskService (ARI HTTP) → Asterisk PBX
                                           ↓
                                    PostgreSQL (call persistence)
                                           ↓
                                    Prometheus (metrics scraping)
                                           ↓
                                    Grafana (dashboards)
```

## Configuration

### Environment Variables (from `config/settings.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| **APP_NAME** | Contact Center API | Application name |
| **DEBUG** | false | Debug mode (enables SQL echo) |
| **SECRET_KEY** | *placeholder* | JWT secret (MUST change in prod) |
| **DATABASE_URL** | postgresql://... | PostgreSQL connection string |
| **DISABLE_DB** | false | Run in minimal mode without DB |
| **ARI_HTTP_URL** | http://localhost:8088/ari | Asterisk ARI endpoint |
| **ARI_USERNAME** | ariuser | ARI credentials |
| **ARI_PASSWORD** | aripass | ARI credentials |
| **ARI_APP** | contactcenter | Stasis application name |
| **DEFAULT_CONTEXT** | outbound-ivr | Dialplan context |
| **DEFAULT_EXTENSION** | s | Extension to dial |
| **DEFAULT_PRIORITY** | 1 | Dial priority |
| **DEFAULT_TIMEOUT** | 30000 | Timeout in milliseconds |
| **DEFAULT_CALLER_ID** | Outbound Call | Caller ID |
| **METRICS_ENABLED** | true | Enable /metrics endpoint |
| **DOCS_ENABLED** | true | Enable /docs endpoint |
| **ALLOWED_ORIGINS** | * | CORS origins (comma-separated) |
| **RATE_LIMIT_REQUESTS** | 10 | Rate limit per window |
| **RATE_LIMIT_WINDOW** | 60 | Rate limit window (seconds) |

### Security Best Practices (from code)

1. **Placeholder Detection**: Startup fails if `SECRET_KEY` is placeholder and not in debug mode
2. **No ARI Public Exposure**: ARI is internal-only, accessed via service mesh
3. **Non-root Docker User**: Container runs as `appuser:1000`
4. **Security Options**: `no-new-privileges:true` in docker-compose
5. **HTTPS Enforcement**: Traefik redirects HTTP→HTTPS with Let's Encrypt
6. **Header Hardening**: STS, XSS protection, no-sniff, frame-deny via Traefik middleware

## Deployment

### Docker Compose Stack (`docker-compose.yml`)

| Service | Image | Exposed | Networks |
|---------|-------|---------|----------|
| **postgres** | postgres:15.5-alpine | No | internal-net |
| **api** | Built from Dockerfile | Via Traefik | internal-net, public-net |
| **prometheus** | prom/prometheus:v2.54.1 | No | internal-net |
| **grafana** | grafana/grafana:10.4.5 | No | internal-net |
| **traefik** | traefik:v2.11 | 80, 443 | public-net, internal-net |

**Note**: Asterisk service is **not included** in docker-compose. Deploy separately or add custom service.

### Volumes
- `postgres_data`: PostgreSQL persistence
- `prometheus_data`: Metrics storage
- `grafana_data`: Dashboard configs
- `./uploads`, `./audio`, `./logs`: App directories

## Testing

### Test Structure (`tests/`)

1. **conftest.py**: Shared fixtures
   - `client`: FastAPI TestClient
   - `mock_asterisk_service`: Mocked ARI service
   - `mock_db`: Mocked database session
   - Sample data fixtures

2. **test_auth.py**: Authentication tests (15 lines)
3. **test_interaction.py**: Call origination/status endpoints (101 lines)
4. **test_asterisk.py**: Asterisk service unit tests (128 lines)

### Running Tests
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (requires pytest)
pytest tests/

# With coverage
pytest --cov=app tests/
```

## Code Quality Observations

### Strengths ✅

1. **Clean Architecture**: Clear separation of concerns (routes, services, models, config)
2. **Async/Await**: Proper async handling with httpx and FastAPI
3. **Error Handling**: Try-except blocks with proper rollback and logging
4. **Structured Logging**: Loguru with JSON middleware for production-ready logs
5. **Type Hints**: Pydantic models for request/response validation
6. **Metrics**: Comprehensive Prometheus instrumentation
7. **Security**: JWT auth, rate limiting, bcrypt hashing, Docker hardening
8. **Dual Mode**: Supports dev (no DB) and production (with DB) configurations
9. **Retry Logic**: Exponential backoff for ARI calls
10. **Documentation**: OpenAPI/Swagger auto-generated, README with examples

### Areas for Improvement 🔧

1. **Database Dependency in Tests**: Tests don't fully mock DB (potential integration test leakage)
2. **Rate Limiter**: In-memory only (not distributed-safe for multi-instance deployments)
3. **Metrics Naming**: Legacy metrics have double `_total` suffix (V2 metrics fix this)
4. **Missing Monitoring Configs**: `monitoring/prometheus.yml` and `monitoring/alerts.yml` deleted (git status shows unstaged deletions)
5. **No Call Status Updates**: No WebSocket or polling mechanism to update call status from Asterisk events (StasisStart, ChannelDestroyed, etc.)
6. **Hardcoded Retry Count**: 3 retries in ARI service (could be configurable)
7. **No Circuit Breaker**: No protection against cascading failures if Asterisk is down
8. **Test Coverage**: Only 316 lines of tests for 1,165 lines of code (~27% coverage)

## Dependencies (`requirements.txt`)

### Core
- **fastapi**: 0.117.1 (Web framework)
- **uvicorn**: 0.36.0 (ASGI server)
- **pydantic**: 2.11.9 (Data validation)
- **pydantic-settings**: 2.10.1 (Config management)
- **SQLAlchemy**: 2.0.43 (ORM)
- **psycopg2-binary**: 2.9.10 (PostgreSQL driver)

### HTTP & Auth
- **httpx**: 0.28.1 (Async HTTP client for ARI)
- **python-jose**: 3.3.0 (JWT encoding/decoding)
- **passlib[bcrypt]**: 1.7.4 (Password hashing)
- **python-multipart**: 0.0.20 (Form data parsing)

### Monitoring & Logging
- **prometheus_client**: 0.23.1 (Metrics)
- **loguru**: 0.7.3 (Structured logging)

### Utilities
- **python-dotenv**: 1.1.1 (.env file support)
- **cryptography**: 46.0.1 (Cryptographic operations)

## Recent Changes (Git History)

```
3afd64e (HEAD -> main) rm .md files
80b68fb (origin/main) changes made
2e72a55 changes made
e75ecfe changes
c072060 first changes
```

**Unstaged Deletions**:
- Documentation files: `IMPROVEMENTS_APPLIED.md`, `REVIEW_SUMMARY.md`, deployment docs
- Monitoring configs: `monitoring/prometheus.yml`, `monitoring/alerts.yml`
- Deployment script: `deploy.sh`

## Scope Alignment with Instructions ✅

The project **perfectly aligns** with the copilot instructions:

✅ **Purpose**: Single outbound call origination, no campaigns  
✅ **Endpoints**: `/api/v2/interaction/{number}`, `/api/v2/status/{call_id}`, `/api/v2/calls`  
✅ **Tech Stack**: Python, FastAPI, PostgreSQL, Asterisk ARI, Docker, Traefik, Prometheus, Grafana  
✅ **Auth**: OAuth2 Password Grant with JWT, bcrypt hashing  
✅ **Dual Mode**: `DISABLE_DB=true` for local dev  
✅ **Security**: SECRET_KEY validation, no public ARI exposure, HTTPS enforcement  
✅ **Out of Scope**: No campaigns, predictive dialing, inbound flows, multi-tenant features  

## Recommendations

### Immediate Actions
1. **Restore Monitoring Configs**: Re-add `monitoring/prometheus.yml` and `monitoring/alerts.yml` or commit deletions
2. **Add Call Status Updates**: Implement WebSocket listener for Asterisk ARI events to update call statuses in DB
3. **Increase Test Coverage**: Add integration tests with real DB (SQLite in-memory) and expand to 60%+ coverage
4. **Document API**: Add request/response examples to docstrings for auto-generated docs

### Long-Term Improvements
1. **Distributed Rate Limiting**: Replace in-memory limiter with Redis-backed solution for multi-instance deployments
2. **Circuit Breaker**: Add resilience patterns (e.g., `tenacity` library) for Asterisk connectivity
3. **Call Recording**: Add support for call recording URLs in Call model
4. **Webhooks**: Support callback URLs for call status updates
5. **Admin UI**: Optional web dashboard for call monitoring (separate from Grafana)

## Conclusion

This is a **well-architected, production-ready** API for outbound IVR dialing via Asterisk. The code is clean, follows best practices, and includes essential features like auth, metrics, and dual-mode operation. With minor improvements to testing and monitoring, this project is ready for deployment in a production contact center environment.

---

**Generated**: 2025-01-XX  
**Analyzer**: GitHub Copilot CLI
