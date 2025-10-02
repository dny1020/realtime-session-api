# Architecture Decision Records (ADR)

This document contains the key architectural decisions made during the development of the Contact Center API.

## ADR-001: FastAPI Framework Selection

**Date:** 2025-09-15

**Status:** Accepted

**Context:**
We needed to select a Python web framework for building a high-performance outbound call API.

**Decision:**
We chose FastAPI over alternatives like Flask, Django, or Tornado.

**Rationale:**
- **Performance**: FastAPI is built on Starlette and Pydantic, offering excellent performance comparable to NodeJS and Go
- **Type Safety**: Native support for Python type hints with automatic validation
- **Auto-documentation**: Automatic OpenAPI (Swagger) documentation generation
- **Async Support**: First-class async/await support for non-blocking I/O
- **Modern**: Uses modern Python 3.7+ features
- **Developer Experience**: Excellent error messages and IDE support

**Consequences:**
- Positive: Fast development, excellent performance, built-in docs
- Negative: Requires Python 3.7+, smaller ecosystem than Flask/Django

---

## ADR-002: Synchronous Call Processing (No Celery)

**Date:** 2025-09-20

**Status:** Accepted

**Context:**
We needed to decide whether to process calls synchronously or use a task queue like Celery.

**Decision:**
We process calls synchronously via direct Asterisk ARI calls without a task queue.

**Rationale:**
- **Simplicity**: Reduces infrastructure complexity (no Redis/RabbitMQ required)
- **Single Call Focus**: API is designed for per-call operations, not bulk campaigns
- **Immediate Feedback**: Clients get instant success/failure response
- **Lower Latency**: No queue overhead for single calls
- **Easier Debugging**: Simpler error tracking without distributed tracing

**Consequences:**
- Positive: Simple architecture, immediate feedback, easier to deploy
- Negative: Limited horizontal scaling for high-volume scenarios
- Future Consideration: Add Celery if bulk campaign features are needed

---

## ADR-003: PostgreSQL for Production, Optional DB Mode

**Date:** 2025-09-22

**Status:** Accepted

**Context:**
We needed a reliable database solution that could also be disabled for testing/minimal deployments.

**Decision:**
Use PostgreSQL as the primary database with an optional `DISABLE_DB=true` mode.

**Rationale:**
- **PostgreSQL Strengths**: ACID compliance, excellent performance, robust JSON support
- **Not SQLite**: Production requires concurrent connections and better reliability
- **Optional Mode**: Allows testing and minimal deployments without database dependency
- **Industry Standard**: Well-supported, excellent tooling, managed services available

**Consequences:**
- Positive: Reliable data persistence, production-ready, flexible deployment
- Negative: Requires PostgreSQL infrastructure in production
- Trade-off: Increased complexity vs. reliability

---

## ADR-004: REST API over GraphQL

**Date:** 2025-09-18

**Status:** Accepted

**Context:**
We needed to choose an API architecture for external clients.

**Decision:**
Implement a RESTful API instead of GraphQL or gRPC.

**Rationale:**
- **Simplicity**: REST is well-understood and easier to implement
- **Use Case**: Simple CRUD operations don't benefit from GraphQL flexibility
- **Tooling**: Better tooling support (curl, Postman, standard HTTP clients)
- **Caching**: Standard HTTP caching works out of the box
- **Documentation**: OpenAPI/Swagger is mature and widely adopted

**Consequences:**
- Positive: Easy to use, wide client support, standard tooling
- Negative: Less flexible than GraphQL for complex queries
- Future: Could add GraphQL endpoint if needed for dashboard/analytics

---

## ADR-005: JWT Authentication with bcrypt

**Date:** 2025-09-25

**Status:** Accepted

**Context:**
We needed a secure, stateless authentication mechanism.

**Decision:**
Use JWT tokens with bcrypt password hashing.

**Rationale:**
- **Stateless**: No server-side session storage required
- **Scalable**: Works seamlessly across multiple API instances
- **Standard**: Industry-standard approach with good library support
- **bcrypt**: Slow hashing algorithm designed for passwords
- **Flexible**: Easy to add claims (roles, permissions) later

**Consequences:**
- Positive: Scalable, standard, no session storage
- Negative: Token revocation requires additional mechanisms
- Security: Tokens can't be revoked without a blacklist/database check

---

## ADR-006: In-Memory Rate Limiting (Temporary)

**Date:** 2025-09-26

**Status:** Accepted (Temporary)

**Context:**
We needed basic rate limiting to prevent abuse of the token endpoint.

**Decision:**
Implement simple in-memory rate limiting with deque-based token bucket.

**Rationale:**
- **Simplicity**: No external dependencies (Redis) required for MVP
- **Sufficient**: Adequate for single-instance deployments
- **Configurable**: Rate limits can be adjusted via environment variables
- **Temporary**: Clearly documented as non-distributed

**Consequences:**
- Positive: Simple, no infrastructure dependencies
- Negative: Won't work across multiple instances
- Future: Replace with Redis-based rate limiting or Traefik plugin for production scale

---

## ADR-007: Prometheus + Grafana for Observability

**Date:** 2025-09-28

**Status:** Accepted

**Context:**
We needed monitoring and metrics collection for production deployments.

**Decision:**
Use Prometheus for metrics collection and Grafana for visualization.

**Rationale:**
- **Industry Standard**: Prometheus is the de facto standard for metrics
- **Pull-Based**: Prometheus scrapes metrics, reducing API overhead
- **Flexible**: Powerful query language (PromQL)
- **Ecosystem**: Excellent tooling, alerting, and dashboard support
- **Low Cardinality**: Designed for time-series data with controlled cardinality

**Consequences:**
- Positive: Excellent observability, powerful queries, great dashboards
- Negative: Additional services to deploy and maintain
- Trade-off: Infrastructure complexity vs. production visibility

---

## ADR-008: Structured JSON Logging with Loguru

**Date:** 2025-09-29

**Status:** Accepted

**Context:**
We needed consistent, structured logging for production debugging and log aggregation.

**Decision:**
Use Loguru for logging with structured JSON output.

**Rationale:**
- **Loguru**: Simple, powerful logging library with excellent API
- **Structured**: JSON logs are machine-parsable (ELK, Loki, etc.)
- **Context**: Easy to add request IDs, user info, etc.
- **Performance**: Asynchronous logging doesn't block requests
- **Developer Experience**: Much better than standard logging module

**Consequences:**
- Positive: Easy to use, structured output, great for log aggregation
- Negative: Another dependency (but lightweight)
- Future: Integrate with centralized logging (Loki, Elasticsearch, etc.)

---

## ADR-009: Alembic for Database Migrations

**Date:** 2025-09-30

**Context:**
We needed a reliable way to manage database schema changes.

**Decision:**
Use Alembic for database migrations instead of SQLAlchemy's `create_all()` in production.

**Rationale:**
- **Version Control**: Migrations are versioned and trackable
- **Rollback**: Can safely rollback schema changes
- **Team Collaboration**: Prevents schema conflicts
- **Production Safety**: Controlled, reviewable schema changes
- **SQLAlchemy Integration**: Works seamlessly with our ORM

**Consequences:**
- Positive: Safe schema evolution, team collaboration, production-ready
- Negative: Requires migration management discipline
- Best Practice: Never use `create_all()` in production

---

## ADR-010: Docker + Docker Compose for Deployment

**Date:** 2025-10-01

**Status:** Accepted

**Context:**
We needed a consistent deployment strategy across environments.

**Decision:**
Use Docker for containerization and Docker Compose for local/staging orchestration.

**Rationale:**
- **Consistency**: Same environment in dev, staging, and production
- **Dependencies**: All dependencies bundled in container
- **Isolation**: Service isolation and resource limits
- **Portability**: Deploy anywhere Docker runs
- **Orchestration**: Docker Compose for simple multi-service setup

**Consequences:**
- Positive: Consistent environments, easy deployment, isolated services
- Negative: Docker learning curve, additional layer
- Future: Consider Kubernetes for large-scale production deployments

---

## ADR-011: Traefik as Reverse Proxy

**Date:** 2025-10-01

**Status:** Accepted

**Context:**
We needed HTTPS, automatic SSL certificates, and routing for production.

**Decision:**
Use Traefik as the reverse proxy and edge router.

**Rationale:**
- **Auto SSL**: Automatic Let's Encrypt certificate management
- **Docker Integration**: Native Docker label-based configuration
- **Modern**: Built for cloud-native and microservices
- **Dashboard**: Built-in monitoring dashboard
- **Rate Limiting**: Can handle rate limiting at edge

**Consequences:**
- Positive: Easy SSL management, great Docker integration, modern
- Negative: Another service to learn and maintain
- Alternative: Nginx is more mature but requires more manual configuration

---

## Future Considerations

### Potential Future ADRs:
1. **Caching Strategy**: Redis for caching user lookups and call status
2. **Distributed Tracing**: OpenTelemetry for request tracing
3. **Message Queue**: Celery + Redis for bulk campaign features
4. **GraphQL**: Additional GraphQL endpoint for complex analytics queries
5. **Kubernetes**: Migration from Docker Compose to K8s for scale
6. **Circuit Breaker**: Implement circuit breaker pattern for Asterisk calls
7. **Feature Flags**: LaunchDarkly or similar for feature toggles
8. **API Gateway**: Kong or similar for advanced API management
