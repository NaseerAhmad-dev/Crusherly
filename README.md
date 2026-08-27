# Stone Crusher Management Platform

A production-grade, multi-tenant Stone Crusher Management Platform, built as a **modular monolith** in a single repository.

This repository currently implements **Phase 0 — Platform Foundation** (identity, tenancy, organization hierarchy,
RBAC + scope-based authorization, audit, document numbering, fiscal year, workflow/approval foundation,
attachments, notifications, settings, units of measurement, locations, cost/profit centres, an internal event
abstraction, a background-job abstraction, and the shared frontend architecture) plus two business modules built
on top of that foundation: **Phase 2 — Weighbridge** ([docs/weighbridge.md](docs/weighbridge.md))
and **Phase 3 — Production** ([docs/production.md](docs/production.md)). Phase 1 — Master Data Foundation — was
skipped and is being built out of order; see [docs/phases/phase-3-completion.md](docs/phases/phase-3-completion.md)
for why. The full phase plan lives in
[Stone_Crusher_Platform_Master_Build_Specification.md](Stone_Crusher_Platform_Master_Build_Specification.md)
(the remaining business modules — Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel, Finance,
Quality, Safety, Compliance, Reporting/Analytics — are added in later phases per that plan; see also
[docs/architecture.md](docs/architecture.md)).

## Repository Layout

```text
stone-crusher/
├── backend/            FastAPI modular monolith (Python 3.12+, SQLAlchemy 2.x async, PostgreSQL, Alembic)
├── frontend/            Angular (strict TypeScript) admin/operations UI
├── infrastructure/       Bicep templates for Azure
├── docs/                 Architecture, module, and process documentation
├── docker-compose.yml    Local dev stack (PostgreSQL + backend + frontend)
├── azure-pipelines.yml   CI/CD pipeline definition
└── .gitignore
```

## Quick Start (Local Development)

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- (Optional, for running outside Docker) Python 3.12+, Node.js 20+, PostgreSQL 16+

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit the generated `.env` files if you need non-default ports/secrets. **Never commit `.env`.**

### 2. Start the stack

```bash
docker compose up --build
```

This starts:

- `postgres` — PostgreSQL 16 with a health check
- `backend` — FastAPI on http://localhost:8000 (docs at `/api/v1/docs`, health at `/health`, readiness at `/ready`)
- `frontend` — Angular dev server on http://localhost:4200

### 3. Run database migrations

Migrations run automatically on backend container start (see `backend/entrypoint.sh`). To run manually:

```bash
docker compose exec backend alembic upgrade head
```

### 4. Seed initial data (roles, a platform super admin, a demo tenant)

```bash
docker compose exec backend python -m app.core.seed
```

## Running Without Docker

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

## Testing

```bash
# Backend
cd backend
pytest -v

# Frontend
cd frontend
npm test
```

## Documentation

See [docs/](docs/) for architecture, database, authentication, authorization, multi-tenancy, organization,
audit, workflow, documents, notifications, weighbridge, production, API conventions, testing, Azure, security,
and development guides, and [docs/adr/](docs/adr/) for Architecture Decision Records. Phase completion reports
live in [docs/phases/](docs/phases/) — see [docs/phases/phase-3-completion.md](docs/phases/phase-3-completion.md)
for the current phase's verified status against its Definition of Done.

## Phase Discipline

This repository is built **phase by phase** per the Master Build Specification. Do not implement future business
modules (Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel, Finance,
Quality, Safety, Compliance, Reporting/Analytics) until their phase is reached and the current phase's Definition
of Done is met.
