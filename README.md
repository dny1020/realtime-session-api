# Contact Center API - Production Ready

Minimal Python FastAPI service for triggering **single outbound IVR calls** via Asterisk ARI. Focused on per-number call origination and real-time status tracking.

## ✨ Features

- 🎯 **Single Call Origination**: Trigger outbound calls to specific numbers
- 📊 **Real-time Status Updates**: WebSocket connection to Asterisk ARI for live call status
- 🔐 **JWT Authentication**: Secure OAuth2 password grant with bcrypt
- 🗄️ **PostgreSQL Persistence**: Call records and user management
- 🐳 **Docker Ready**: Production-ready Docker Compose setup
- 📝 **RESTful API**: Clean REST endpoints with OpenAPI/Swagger docs

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Asterisk server with ARI enabled (deployed separately)

### 1. Clone and Configure

```bash
# Clone repository
git clone <your-repo>
cd api_contact_center

# Create environment file
cp .env.example .env

# Generate secrets
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 24  # For POSTGRES_PASSWORD
```

### 2. Update .env

```env
SECRET_KEY=<your-generated-secret>
POSTGRES_PASSWORD=<your-db-password>
ARI_HTTP_URL=http://your-asterisk-server:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=<your-ari-password>
```

### 3. Start Services

```bash
# Start API and database
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### 4. Create User

```bash
docker-compose run --rm api python -m app.auth.create_user
```

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v2/token` | Get JWT token | No |
| POST | `/api/v2/interaction/{number}` | Originate call | Yes |
| GET | `/api/v2/status/{call_id}` | Get call status | Yes |
| POST | `/api/v2/calls` | Create call (RESTful) | Yes |
| GET | `/api/v2/calls/{call_id}` | Get call details | Yes |
| GET | `/health` | Health check | No |
| GET | `/docs` | API documentation | No |

## 🔌 Usage Examples

### Get Authentication Token

```bash
curl -X POST http://localhost:8000/api/v2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

### Make an Outbound Call

```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/api/v2/interaction/+1234567890 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "outbound-ivr",
    "extension": "s",
    "timeout": 30000,
    "caller_id": "MyCompany"
  }'
```

Response:
```json
{
  "success": true,
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "message": "Call originated successfully",
  "channel": "550e8400-e29b-41d4-a716-446655440000",
  "status": "dialing",
  "created_at": "2025-01-05T12:00:00Z"
}
```

### Check Call Status

```bash
curl -X GET http://localhost:8000/api/v2/status/{call_id} \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "phone_number": "+1234567890",
  "status": "answered",
  "channel": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-05T12:00:00Z",
  "answered_at": "2025-01-05T12:00:05Z",
  "duration": 45,
  "is_active": false,
  "is_completed": true
}
```

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐      ┌──────────────┐
│  FastAPI    │◄────►│  PostgreSQL  │
│     API     │      │   Database   │
└──────┬──────┘      └──────────────┘
       │
       │ ARI HTTP + WebSocket
       ▼
┌─────────────┐
│  Asterisk   │
│     PBX     │
└─────────────┘
```

### Key Components

- **FastAPI**: REST API with async/await
- **PostgreSQL**: Call records and user storage
- **Asterisk ARI**: Call control via HTTP + WebSocket for real-time events
- **JWT Auth**: Secure token-based authentication

## 🔧 Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Asterisk ARI (external service)
ARI_HTTP_URL=http://asterisk-server:8088/ari
ARI_USERNAME=ariuser
ARI_PASSWORD=secure_password
ARI_APP=contactcenter

# Security
SECRET_KEY=your-secret-key
JWT_ISSUER=your-issuer
JWT_AUDIENCE=your-audience

# Call Defaults
DEFAULT_CONTEXT=outbound-ivr
DEFAULT_EXTENSION=s
DEFAULT_TIMEOUT=30000
DEFAULT_CALLER_ID=Outbound Call
```

## 🎛️ Asterisk Configuration

Configure ARI in `/etc/asterisk/ari.conf`:

```ini
[general]
enabled = yes

[ariuser]
type = user
read_only = no
password = your_password
```

Create dialplan in `/etc/asterisk/extensions.conf`:

```ini
[outbound-ivr]
exten => _X.,1,NoOp(Outbound call to ${EXTEN})
 same => n,Answer()
 same => n,Stasis(contactcenter)
 same => n,Playback(welcome)
 same => n,Hangup()
```

## 📊 Call Status Flow

The API tracks calls through these states:

1. **pending**: Call created in database
2. **dialing**: Channel created, dialing started
3. **ringing**: Remote party ringing
4. **answered**: Call answered
5. **completed**: Call ended successfully
6. **failed/busy/no_answer**: Call failed with specific reason

Status updates happen **automatically** via WebSocket events from Asterisk.

## 🐳 Docker Services

```yaml
services:
  postgres:    # PostgreSQL database
  api:         # FastAPI application
```

Note: **Asterisk is deployed separately** as an external service.

## 📦 Production Deployment

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for:
- SSL/HTTPS setup with Nginx or Traefik
- Database migrations
- Backup strategies
- Scaling considerations
- Security checklist

## 🧪 Development

### Local Setup (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Create user
python -m app.auth.create_user

# Start server
uvicorn app.main:app --reload
```

### Run Tests

```bash
pytest tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🔒 Security Features

- ✅ JWT token authentication with bcrypt password hashing
- ✅ Rate limiting on token endpoint (10 req/60s)
- ✅ SECRET_KEY validation at startup
- ✅ Non-root Docker user
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ Input validation (Pydantic models)
- ✅ CORS configuration
- ✅ No public exposure of Asterisk ARI

## 📝 API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🛠️ Tech Stack

- **Python 3.11+**
- **FastAPI 0.117+**: Modern async web framework
- **SQLAlchemy 2.0**: ORM
- **PostgreSQL 15**: Database
- **Alembic**: Database migrations
- **httpx**: Async HTTP client
- **websockets**: Real-time ARI events
- **python-jose**: JWT handling
- **passlib**: Password hashing
- **loguru**: Structured logging

## 📄 License

[Your License]

## 🤝 Contributing

[Contributing guidelines]

## 📧 Support

[Support information]
