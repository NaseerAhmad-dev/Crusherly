# Azure

This document covers what exists today: the CI/CD pipeline (`azure-pipelines.yml`), the Docker
images, and the Azure service integrations wired into application code (Key Vault, Application
Insights, Blob Storage). It ends with a clearly-scoped [Not yet built](#not-yet-built) section —
there is currently no infrastructure-as-code that actually provisions any Azure resource.

## CI/CD pipeline (`azure-pipelines.yml`)

Triggers on pushes and PRs against `main` and `develop`. Six stages, each gated on the previous
one succeeding:

1. **Install** — two parallel jobs: `pip install -e ".[dev]"` for the backend, `npm ci` for the
   frontend. (Ubuntu-hosted agents, Python 3.12, Node 20.x.)
2. **Lint** — `ruff check app tests` + `black --check app tests` for the backend; `npm run lint`
   (ESLint via `angular-eslint`) for the frontend.
3. **Test** — `pytest --maxfail=1 --disable-warnings --cov=app` for the backend, run against a
   real `postgres` service container
   (`DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres`), not SQLite —
   see [testing.md](testing.md) for why the local/CI split doesn't hide dialect-specific bugs;
   `npm test -- --watch=false --browsers=ChromeHeadless` for the frontend.
4. **SecurityChecks** — `pip-audit` and `npm audit --audit-level=high`, both suffixed `|| true`:
   findings are surfaced in the pipeline log but do not fail the build today.
5. **Build** — `npm run build -- --configuration production` (Angular production build). There is
   no equivalent backend "build" step beyond what the Docker stage does — the backend has no
   compiled build artifact.
6. **DockerBuildPush** — gated on
   `and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))` (main branch only).
   Builds and pushes both `backend/Dockerfile` and `frontend/Dockerfile` to
   `$(azureContainerRegistryServiceConnection)`, tagged with both `$(Build.BuildId)` and `latest`.
   **This service connection is referenced but not defined anywhere in this repo** — it has to
   exist as an Azure DevOps project/service-connection configuration outside version control.
7. **DeployDevelopment** — also main-branch-only. This is a literal placeholder: its one step is
   `echo "Deploy $(backendImage):$(Build.BuildId) and $(frontendImage):$(Build.BuildId) to Azure
   Container Apps / App Service (Development)."`, explicitly labeled
   `(placeholder — see infrastructure/README.md)`. **`infrastructure/README.md` does not exist in
   this repo.** Nothing in this pipeline has ever actually deployed the application anywhere.

A trailing comment documents the intended promotion path, none of which is implemented yet:

```text
Development -> Testing -> Staging -> Approval -> Production
Credentials must come from Azure Key Vault / pipeline variable groups linked to service
connections — never place secrets directly in this YAML.
```

## Docker images

### `backend/Dockerfile`

- `python:3.12-slim` base.
- Installs the package with the `azure` extra unconditionally (`pip install ".[azure]"`) rather
  than maintaining a separate "production" image variant. The Dockerfile's own comment explains
  why: the same image has to work whether `STORAGE_PROVIDER=azure` and/or Application Insights are
  turned on via environment variables at runtime, so the SDKs need to already be present
  regardless.
- Runs as a non-root `appuser` (uid 1000).
- `ENTRYPOINT ["./entrypoint.sh"]`, which runs `alembic upgrade head` and then
  `exec uvicorn app.main:app --host 0.0.0.0 --port 8000` — migrations run automatically on every
  container start, not as a separate deploy step.

### `frontend/Dockerfile`

- `node:22-slim` base, and it is a **development-only image**: `npm install`, then
  `CMD ["npm", "start"]` (`ng serve`), intended to run against a bind-mounted source tree (see
  `docker-compose.yml`'s `./frontend:/app` volume) for live reload.
- The Dockerfile's own comment states production builds/serving are explicitly out of scope for
  it: "Production builds/serving are handled by the CI 'Build' stage (`ng build`) and a separate
  hosting target (Azure Static Web Apps / Container App + nginx) — not by this Dockerfile."
  **No such production frontend image or nginx config exists in this repo yet** — the
  `DockerBuildPush` stage still builds and pushes this same dev-server `frontend/Dockerfile`
  image, since it's the only frontend Dockerfile that exists.

### `docker-compose.yml`

Local development only — there is no production or staging compose file in this repo.

- `postgres` — `postgres:16-alpine`, with a `pg_isready` healthcheck.
- `backend` — built from `backend/Dockerfile`, loads `backend/.env`, overrides `DATABASE_URL` to
  point at the `postgres` service, waits on its healthcheck (`condition: service_healthy`), and
  has its own healthcheck hitting `/health`. Source is bind-mounted (`./backend:/app`).
- `frontend` — built from `frontend/Dockerfile`, loads `frontend/.env`, depends on `backend` (no
  healthcheck gate, just startup ordering), bind-mounts source with an anonymous volume over
  `/app/node_modules` so the host's `node_modules` (or lack of one) doesn't shadow the container's
  installed copy.

## Azure integration points in application code

### Key Vault — environment-variable injection, not a direct SDK call

`app/core/config.py`'s module docstring states the intended pattern directly: *"Local secrets
live in `.env` (never committed); production secrets are injected via Azure Key Vault into the
same environment variable names, so no code branches on where the secret physically lives."*
`Settings` declares `azure_key_vault_url: str = ""`, but **no code under `app/` actually calls the
Key Vault SDK** — there is no `SecretClient`, no `azure-identity` credential lookup at runtime;
`azure_key_vault_url` is a settings field with no reader. The real mechanism today is meant to be
external to the application: Key Vault-backed pipeline variable groups populating the deployment
environment's variables, per the promotion-path comment in `azure-pipelines.yml` quoted above —
but no variable group is actually defined in this repo either. In short: the app is *shaped* to
accept Key Vault-sourced config without any code change, but the Key Vault side of that wiring
doesn't exist yet.

### Application Insights — real, working code path

`app/core/logging_config.py`'s `configure_logging()` always installs a stdout `StreamHandler`,
and additionally attaches an `AzureLogHandler` (from `opencensus-ext-azure`, part of the `azure`
extra) whenever `settings.applicationinsights_connection_string` is non-empty:

```python
if settings.applicationinsights_connection_string:
    try:
        from opencensus.ext.azure.log_exporter import AzureLogHandler
        azure_handler = AzureLogHandler(connection_string=settings.applicationinsights_connection_string)
        azure_handler.addFilter(RequestIdFilter())
        root.addHandler(azure_handler)
    except Exception:
        logging.getLogger(__name__).warning(..., exc_info=True)
```

This is genuinely wired up, not a stub: set `APPLICATIONINSIGHTS_CONNECTION_STRING` in the
environment and every log line (already tagged with the request correlation ID via
`RequestIdFilter`) ships to Application Insights. The `try/except` means a bad or unreachable
connection string degrades to a logged warning rather than crashing startup.

### Blob Storage — real, working code path, selected by configuration

`app/services/storage_service.py` defines a `StorageProvider` ABC
(`upload`/`download`/`delete`/`generate_access_url`) with two implementations:

- `LocalStorageProvider` — default (`STORAGE_PROVIDER=local`), writes under
  `settings.local_storage_path`, guards against path traversal in `_resolve()`, and serves files
  back through the API itself (`generate_access_url` returns
  `/api/v1/attachments/local/{key}`, since local dev has no public URL).
- `AzureBlobStorageProvider` — used when `STORAGE_PROVIDER=azure`. Wraps
  `azure.storage.blob.aio.BlobServiceClient` for upload/download/delete, and
  `generate_access_url` issues a real time-limited SAS URL via `generate_blob_sas`
  (`BlobSasPermissions(read=True)`, expiring `expires_in_seconds` after the call).

`get_storage_provider()` is a module-level singleton selected purely by
`settings.storage_provider`; callers (`app/services/attachment_service.py`) depend only on the
`StorageProvider` protocol, so switching providers is a configuration change
(`STORAGE_PROVIDER` + `AZURE_STORAGE_CONNECTION_STRING` + `AZURE_STORAGE_CONTAINER`), not a code
change.

### The `azure` extra

`backend/pyproject.toml` keeps `azure-storage-blob`, `azure-identity`, and `opencensus-ext-azure`
out of the base install (`pip install -e ".[dev]"` doesn't pull them in) to avoid a slow
dependency tree in local dev/CI paths that never exercise Azure Blob or App Insights.
`backend/Dockerfile` installs `".[azure]"` explicitly instead, so every built image has these SDKs
available regardless of whether the corresponding environment variables are actually set at
runtime.

## Not yet built

- **`infrastructure/bicep/` is an empty directory.** There is no Bicep (or any other IaC) checked
  in — no template for PostgreSQL, Container Apps/App Service, Azure Container Registry, Key
  Vault, Application Insights, Storage Account, networking, or anything else. Every Azure resource
  this document describes integrating with has to be provisioned by hand today.
- **`infrastructure/README.md`, referenced by the pipeline's `DeployDevelopment` placeholder
  comment, does not exist.** In fact `infrastructure/` contains no files at all outside the empty
  `bicep/` subdirectory.
- **No real deployment stage.** `DeployDevelopment` is a single `echo` step; there is no
  `Testing`, `Staging`, or `Production` stage implemented at all, beyond the trailing comment
  describing the intended promotion path.
- **The Docker registry service connection (`$(azureContainerRegistryServiceConnection)`) is
  undefined in-repo** — it would need to be created in Azure DevOps project settings before
  `DockerBuildPush` could succeed.
- **No Key Vault wiring beyond a settings field.** `azure_key_vault_url` exists on `Settings` but
  is not read by any code, and no pipeline variable group backed by Key Vault is defined.
- **No production frontend image.** `frontend/Dockerfile` is the dev server only; the Static Web
  Apps/Container App + nginx target mentioned in its own comment doesn't exist.
