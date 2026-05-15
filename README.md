# Certifactory

A web-based PKI certificate management platform for creating and managing Certificate Authorities, issuing certificates, and handling the full certificate lifecycle.

## Features

- **Flexible CA Hierarchy** — Create root and intermediate CAs to any depth. Any CA can issue end-entity certificates or sign subordinate CAs.
- **Certificate Lifecycle** — Issue, approve, deny, revoke, renew, and download certificates in PEM, DER, and PKCS12 formats.
- **CSR Submission** — Accept and sign Certificate Signing Requests from external systems.
- **Import** — Import existing CAs and certificates from PEM, DER, or PKCS12 files with auto-detection of parent CA relationships.
- **Approval Workflow** — Configurable per CA: auto-issue or require operator approval before signing.
- **OCSP Responder** — Built-in RFC 6960 OCSP responder with configurable signing mode (CA key or dedicated OCSP signing certificate).
- **CRL Generation** — Automatic CRL regeneration on a configurable schedule per CA.
- **Role-Based Access Control** — Four roles: Admin, Operator, Requester, Auditor.
- **Detailed Audit Log** — Tracks all actions with username, resource, IP address, and CSV export.
- **REST API** — API-first design. Every operation available via the API with JWT authentication.
- **Dark/Light Theme** — Obsidian-inspired UI with monochrome icons and color used only for status indicators.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 18, Tailwind CSS, TanStack Query, React Router |
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL (SQLite for local development) |
| Crypto | Python `cryptography` library |
| Proxy | Nginx with TLS termination |

## Quick Start (Docker Compose)

```bash
# Clone the repository
git clone https://github.com/jobongo/certifactory.git
cd certifactory

# Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, PKI_MASTER_KEY, and JWT_SECRET_KEY

# Start all services
docker compose up --build
```

Open **https://localhost** and log in with `admin` / `admin`.

### Services

| Service | Description | Port |
|---------|------------|------|
| proxy | Nginx reverse proxy (TLS termination) | 80, 443 |
| frontend | React SPA served by Nginx | internal |
| backend | FastAPI application | internal |
| db | PostgreSQL 16 | internal |

### SSL Certificates

By default, a self-signed certificate is generated automatically on first start. To use your own certificates:

1. Place your cert and key in a `certs/` directory
2. Set in `.env`:
   ```
   SSL_CERT_DIR=./certs
   SSL_CERT_PATH=/etc/nginx/certs/cert.pem
   SSL_KEY_PATH=/etc/nginx/certs/key.pem
   ```

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173 with API proxy to the backend.

## Environment Variables

| Variable | Description | Default |
|----------|------------|---------|
| `POSTGRES_DB` | Database name | `certifactory` |
| `POSTGRES_USER` | Database user | `certifactory` |
| `POSTGRES_PASSWORD` | Database password | *required* |
| `PKI_MASTER_KEY` | AES-256 key for encrypting private keys at rest | *required* |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | *required* |
| `HTTP_PORT` | Host HTTP port | `80` |
| `HTTPS_PORT` | Host HTTPS port | `443` |
| `SSL_CERT_DIR` | Host directory with SSL certs | `./certs` |
| `SSL_CERT_PATH` | Container path to SSL cert | `/etc/nginx/certs/cert.pem` |
| `SSL_KEY_PATH` | Container path to SSL key | `/etc/nginx/certs/key.pem` |

## User Roles

| Role | Permissions |
|------|------------|
| **Admin** | Full access. Manage users, CAs, certificates, audit logs. |
| **Operator** | Create/manage CAs, issue/approve/revoke certificates, view audit logs. |
| **Requester** | Request certificates, submit CSRs, view own certificates. |
| **Auditor** | Read-only access to CAs, certificates, and audit logs. |

## API

All endpoints are under `/api/v1/`. Authenticate with `POST /api/v1/auth/login` to get a JWT token.

Interactive API documentation is available at:
- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`

## Project Structure

```
certifactory/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── services/        # Business logic and crypto operations
│   │   └── scheduler/       # Background jobs (CRL regen, expiry checks)
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios API client modules
│   │   ├── components/      # UI, layout, form, and shared components
│   │   ├── hooks/           # Auth and theme hooks
│   │   ├── pages/           # Route page components
│   │   └── utils/           # SVG icons
│   └── Dockerfile
├── proxy/                   # Nginx reverse proxy with TLS
├── docker-compose.yml
└── .env.example
```

## License

MIT
