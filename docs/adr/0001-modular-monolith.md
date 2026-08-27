# 1. Modular Monolith Instead of Microservices for Phase 0

## Status

Accepted

## Context

The Stone Crusher Management Platform is a multi-tenant SaaS system that will eventually host a
large number of business modules on top of a shared platform foundation: Weighbridge, Production,
Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel, Finance, Quality, Safety,
Compliance, and Reporting/Analytics, all layered on identity, tenancy, organization hierarchy,
RBAC, scope-based authorization, audit, document numbering, workflow/approval, and notifications
(see the root [README.md](../../README.md)).

At the start of Phase 0 a deployment topology had to be chosen before any business module existed
to prove out real service boundaries. The candidate business modules share the same
tenant/org/RBAC/audit foundation and, in the operations they model, frequently touch several of
those areas within a single logical transaction — e.g. recording a weighbridge ticket touches
inventory, a document sequence, and an audit event together. A microservices split made along
module lines at this stage would have to guess at those boundaries before any real usage existed
to validate them.

## Decision

Build one deployable FastAPI application — a modular monolith — rather than separate services per
module, for the phases covered by the current Master Build Specification.

Internally, the codebase is still cut into modules with real boundaries, enforced by layering
rather than by process/network isolation. Every module follows `api -> service -> repository ->
model` (see `app/main.py`'s docstring and [docs/architecture.md](../architecture.md)): routers
depend only on services, services depend only on repositories, repositories depend only on their
own models, and modules do not import another module's repositories directly. Cross-cutting
concerns — authentication, tenant isolation, RBAC/scope authorization, audit — are implemented
once, in `app/security/` and `app/middleware/`, and used by every module rather than being
duplicated or re-implemented per service.

Where a module needs to react to another module's activity without a direct dependency, it does
so through the in-process event bus (`app/events/bus.py`), not a synchronous call into the other
module's service layer. This keeps the seam for a future extraction (e.g. Reporting/Analytics
under heavy read load) already in place: the service layer is the boundary, and swapping the
event bus's `publish`/`subscribe` implementation for a real broker would not require call sites in
services to change.

## Consequences

**Positive:**

- One thing to build, test, deploy, and roll back: one Docker image per side
  (`backend/Dockerfile`, `frontend/Dockerfile`), one CI pipeline (`azure-pipelines.yml`), one
  Alembic migration chain.
- Cross-module invariants that matter for correctness and security — tenant isolation, RBAC,
  audit — are enforced in one transaction and one place, instead of needing distributed-transaction
  or saga patterns across service boundaries that don't yet have a proven shape.
- No network-hop latency, no service-to-service auth problem, and no version-skew problem between
  modules, since they all ship together.
- Iteration speed is higher while module boundaries are still being discovered — a boundary drawn
  wrong costs a refactor, not a service migration.

**Negative / accepted trade-offs:**

- Module boundaries are enforced by code review and layering convention, not by process
  isolation — nothing currently stops a future contributor from importing another module's
  repository directly, other than review discipline.
- A bug or resource leak in one module can affect the availability of the whole application; there
  is no bulkhead between, say, Reporting and core transaction-processing modules.
- Scaling is coarse-grained: the whole backend scales as one unit today; a module with
  disproportionate load cannot be scaled independently without extraction work first.
- Extracting a module into its own service later is possible but not free — it requires pulling
  shared auth/tenancy logic into something callable across a process boundary, which is
  deliberately deferred until a concrete scaling or ownership need forces it (see
  [docs/architecture.md](../architecture.md)).
