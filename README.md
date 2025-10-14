# Realtime Session API

![CI/CD](https://github.com/dny1020/realtime-session-api/workflows/CI%2FCD%20Pipeline/badge.svg)  
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Realtime Session API** is a lightweight, production-ready FastAPI service for orchestrating **outbound session events** with real-time WebSocket tracking and RESTful control endpoints.  
It’s designed for integration into asynchronous communication systems that require precise event control, monitoring, and state transitions.

---

## ✨ Features

- 🎯 **Session origination** – Initiate and manage real-time outbound sessions  
- 📡 **Live event tracking** – WebSocket stream for status updates and state changes  
- 🔐 **JWT authentication** – Token-based access control with bcrypt-secured credentials  
- 🗄️ **PostgreSQL persistence** – Full lifecycle data management for sessions  
- 🐳 **Docker-ready** – Multi-platform container builds (amd64 / arm64)  
- 🚀 **CI/CD pipeline** – Automated testing, builds, and deployment via GitHub Actions  
- 📝 **Interactive API docs** – Auto-generated OpenAPI documentation  
- ⚡ **Production-ready** – Health checks, structured logging, CORS, and rate limiting  

---

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose**  
- **Python 3.11+** (for local development)  
- **PostgreSQL 15+** (production database)  
- External service or system with event-driven session control  

### Using Makefile (Recommended)

```bash
# Complete setup
make quick-start

# Common tasks
make up          # Start services
make logs        # View logs
make test        # Run tests
make down        # Stop services
```

### Using Docker Compose

```bash
docker pull ghcr.io/dny1020/realtime-session-api:latest
docker-compose up -d
```

### Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DISABLE_DB=true
export SECRET_KEY=local-dev-secret
uvicorn app.main:app --reload
```

Access API docs at:  
`http://localhost:8000/docs`

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|-----------|-------------|------|
| POST | `/api/v1/token` | Obtain JWT token | ❌ |
| POST | `/api/v1/session/{target}` | Initiate outbound session | ✅ |
| GET | `/api/v1/status/{session_id}` | Retrieve session status | ✅ |
| GET | `/health` | Health check | ❌ |

---

## 💡 Example Usage

### Obtain Token
```bash
curl -X POST http://localhost:8000/api/v1/token   -d "username=admin&password=yourpassword"
```

### Start Outbound Session
```bash
TOKEN="your_access_token"

curl -X POST http://localhost:8000/api/v1/session/target123   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   -d '{
    "context": "outbound-context",
    "caller_id": "System <001>"
  }'
```

### Get Session Status
```bash
curl -X GET http://localhost:8000/api/v1/status/abc123   -H "Authorization: Bearer $TOKEN"
```

---

## 🏗️ Architecture Overview

```
┌──────────────┐
│    Client    │
└──────┬───────┘
       │ HTTPS/REST
       ▼
┌────────────────────────────────────┐
│        FastAPI Backend             │
│  - Auth & Validation               │
│  - REST Endpoints                  │
│  - WebSocket Listener              │
│  - Persistence Layer (SQLAlchemy)  │
└───────┬────────────────────────────┘
        │
        ▼
┌────────────────────┐
│  External Engine   │  ← event-driven system
│  (WebSocket/HTTP)  │
└────────────────────┘
```

### Session Lifecycle

```
initiated → pending → active → completed
                       ↘ failed
                       ↘ timeout
```

---

## 🐳 Docker

```bash
docker pull ghcr.io/dny1020/realtime-session-api:latest
docker run -p 8000:8000 realtime-session-api
```

Multi-architecture builds available for **amd64** and **arm64**.

---

## ⚙️ Configuration

| Variable | Description | Required |
|-----------|-------------|-----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `SECRET_KEY` | JWT signing key | ✅ |
| `EXTERNAL_HTTP_URL` | External session engine endpoint | ✅ |
| `EXTERNAL_USERNAME` | Auth username | ✅ |
| `EXTERNAL_PASSWORD` | Auth password | ✅ |
| `DISABLE_DB` | Run without DB (testing) | No |

Minimal `.env`:
```env
DISABLE_DB=true
SECRET_KEY=local-dev-secret
EXTERNAL_HTTP_URL=http://localhost:8088/api
EXTERNAL_USERNAME=user
EXTERNAL_PASSWORD=pass
DEBUG=true
```

---

## 🧪 Development

```bash
pip install -r requirements.txt
make test
black app/ config/ tests/
ruff check app/
```

---

## 🚀 CI/CD

Built on **GitHub Actions**:
- Automated testing & linting  
- Multi-arch Docker builds  
- Smart tagging (`latest`, `v1.0.0`, commit SHA)  
- Security scans with Trivy  

---

## 📦 Tech Stack

- **FastAPI** + **Uvicorn** – async web framework  
- **SQLAlchemy / Alembic** – ORM & migrations  
- **PostgreSQL** – persistent storage  
- **JWT / Bcrypt** – auth & security  
- **Docker / GitHub Actions** – DevOps pipeline  

---

## 🔒 Security

- JWT-based authentication  
- Hashed credentials (bcrypt)  
- Rate limiting on sensitive endpoints  
- CORS and input validation  
- Non-root Docker execution  

---

## 📖 Documentation

Interactive docs:  
- Swagger UI → `/docs`  
- ReDoc → `/redoc`  
- OpenAPI JSON → `/openapi.json`

---

## 🤝 Contributing

1. Fork the repo  
2. Create a feature branch  
3. Submit a pull request with tests  

---

## 📄 License

MIT License – see [LICENSE](LICENSE)

---

**Built for real-time interaction systems and event-driven applications.**
