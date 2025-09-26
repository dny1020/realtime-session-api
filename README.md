# Contact Center API (Outbound IVR Dialer)
Minimal Python (FastAPI) API to trigger single outbound calls through Asterisk, playing prerecorded messages or basic IVRs without human agents. This project focuses only on per-number call origination and call status queries.

---
## Functionality
### Single Calls
  - POST /api/v2/interaction/{number} → Initiate a call to a number via Asterisk ARI
  - Connect the number to an IVR context or audio playback

### Monitoring
  - GET /api/v2/status/{call_id} → Query the status of a call (pending, ringing, answered, failed)

## Technologies
* Python 3.x
* FastAPI → REST API
* Asterisk ARI → Call control/origination (REST/WebSocket)
* PostgreSQL (production) → Persistence for calls. Can be disabled locally.
* Docker (optional) → Packaging and deployment
### Scope:
  - Local: can run without a database by setting DISABLE_DB=true.
  - Production: PostgreSQL required (SQLite not supported).

## Endpoints
  - POST /api/v2/interaction/{number} → Start a call to a number
  - GET /api/v2/status/{call_id} → Get call status
  - POST /api/v2/calls → Create call (body: phone_number, context, …)
  - GET /api/v2/calls/{call_id} → Query call status

## Project Structure

```bash

  contact-center-api/
│── app/
│   ├── main.py         # FastAPI entrypoint
│   ├── routes/         # Routes and controllers
│   ├── services/       # Business logic (Asterisk ARI)
│   ├── models/         # ORM (SQLAlchemy / pydantic)
│   
│
│── config/
│   └── settings.py     # Environment variables
│── README.md
│── requirements.txt
│── Dockerfile

 ```


## Architecture

```bash

  Client[Client\n(curl/Insomnia/Browser)]
  Traefik[(Traefik\n:80/:443)]
  API[FastAPI API\nJWT + /metrics]
  
  Postgres[(PostgreSQL)]
  Asterisk[Asterisk\nARI + PJSIP]
  Prometheus[Prometheus]
  Grafana[Grafana]
  
  Client -->|api.localhost| Traefik --> API
  API --> Postgres
  API -->|ARI (HTTP/WS)| Asterisk
  Prometheus --> API
  Grafana --> Prometheus

 ```

 ## Services

```sql

 | Service       | URL / Port                                                              | Notes                                                      |
| ------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| API (Traefik) | [http://api.localhost](http://api.localhost) (dev) / https://<API_HOST> | FastAPI with `/docs`, `/health`, `/metrics`                |
| Traefik       | Disabled by default                                                     | Dashboard not exposed for security                         |
| Prometheus    | Not exposed by default                                                  | Map port in dev if needed                                  |
| Grafana       | Not exposed by default                                                  | Default dev user/pass: `admin / admin123` (change in prod) |
| Asterisk ARI  | Internal only                                                           | User/pass in `ari.conf`; API connects internally           |
| SIP/PJSIP     | 5060 (internal)                                                         | Expose only for softphone/trunk testing                    |
## Authentication (Production)
- OAuth2 Password Grant to obtain JWT at `POST /api/v2/token` using username/password.
- Passwords are stored hashed (bcrypt). Set `SECRET_KEY` and optionally `JWT_ISSUER`, `JWT_AUDIENCE`.
- Tokens include `sub`, `iat`, `exp`, and optionally `iss`/`aud`.

## Configuration
- Set DATABASE_URL for production (PostgreSQL). Use `DISABLE_DB=true` to run in minimal mode without DB (only for dev/testing; token endpoint requires DB).
- Asterisk ARI settings: `ARI_HTTP_URL`, `ARI_USERNAME`, `ARI_PASSWORD`, `ARI_APP`.
- Default call routing: `DEFAULT_CONTEXT`, `DEFAULT_EXTENSION`, `DEFAULT_PRIORITY`, `DEFAULT_TIMEOUT`, `DEFAULT_CALLER_ID`.
- Metrics: `METRICS_ENABLED` to enable; `/metrics` exposed only when enabled.

## Security
- Use strong `SECRET_KEY` and HTTPS with a reverse proxy (e.g., Traefik, Nginx).
- Restrict access to /docs and /metrics in production (via IP allowlist or auth at the proxy layer).
- Don’t expose Asterisk ARI publicly.

## Run locally
1) Install dependencies
2) Start FastAPI (UVicorn) and Asterisk with ARI available
3) Get a token at `/api/v2/token` then call protected endpoints

## Metrics
- Prometheus metrics at `/metrics` when enabled.
- Low-cardinality labels for reliability; avoid per-ID paths.
 ```


