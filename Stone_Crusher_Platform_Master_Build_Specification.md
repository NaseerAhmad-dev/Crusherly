# Stone Crusher Management Platform
## Master Build Specification & Phase-Wise Implementation Plan

## Purpose

Build a production-grade, multi-tenant Stone Crusher Management Platform as a modular monolith in a single repository.

The platform must have a strong reusable foundation first. Business modules such as Production, Weighbridge, Inventory, Sales, Dispatch, Purchases, Maintenance, Vehicles, Fuel, Finance, Quality, Safety, Compliance, Reporting and Analytics will be added in later phases.

The goal is to avoid redesigning authentication, authorization, tenancy, organization, audit, workflow, documents, notifications, database conventions, frontend architecture, API conventions, CI/CD and Azure deployment later.

---

# 1. Core Principles

1. Security first.
2. Backend is the final security boundary.
3. Multi-tenancy must be enforced server-side.
4. RBAC must support permissions and scopes.
5. Business modules must reuse platform services.
6. Use a modular monolith initially, not microservices.
7. Backend, frontend, infrastructure and documentation remain in one repository.
8. Every database change uses Alembic migrations.
9. Important business transactions must be auditable.
10. Do not directly edit derived balances when a transaction/ledger model is appropriate.
11. Do not over-engineer before there is a real requirement.
12. Every phase must be tested before the next phase begins.

---

# 2. Technology

Unless an existing repository requires otherwise:

## Backend
- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- asyncpg
- Alembic
- Pydantic v2
- pytest
- httpx

## Frontend
- Angular
- TypeScript
- Angular Material or mature enterprise component library
- Strict TypeScript

## Azure
- Azure Database for PostgreSQL
- Azure App Service or Azure Container Apps
- Azure Container Registry
- Azure Key Vault
- Azure Blob Storage
- Azure Application Insights
- Azure DevOps

## Infrastructure
- Docker
- Docker Compose for local development
- Bicep preferred for Azure infrastructure unless existing repository dictates otherwise

---

# 3. Repository Strategy

Use one repository containing:

```text
stone-crusher/
├── backend/
├── frontend/
├── infrastructure/
├── docs/
├── docker-compose.yml
├── azure-pipelines.yml
├── README.md
└── .gitignore
```

A suitable backend structure:

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── security/
│   ├── middleware/
│   ├── events/
│   ├── jobs/
│   └── main.py
├── alembic/
├── tests/
├── pyproject.toml
├── Dockerfile
└── .env.example
```

A suitable frontend structure:

```text
frontend/
├── src/
│   ├── app/
│   │   ├── core/
│   │   ├── shared/
│   │   ├── layout/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── users/
│   │   ├── roles/
│   │   ├── tenants/
│   │   └── settings/
│   └── environments/
├── tests/
├── package.json
├── angular.json
├── Dockerfile
└── .env.example
```

Improve the structure if needed, but document the reason.

---

# 4. Target Architecture

```text
                         PLATFORM
                            |
          +-----------------+-----------------+
          |                 |                 |
       Identity          Tenancy        Organization
          |                 |                 |
          +-----------------+-----------------+
                            |
                       Authorization
                            |
                   RBAC + Permissions
                            |
                      Scope / Access
                            |
          +-----------------+-----------------+
          |                 |                 |
        Audit           Workflow          Settings
          |                 |                 |
          +-----------------+-----------------+
                            |
                     Shared Services
                            |
          +-----------------+-----------------+
          |                 |                 |
      Documents       Notifications     Background Jobs
                            |
                       Business Modules
                            |
       +----------+---------+---------+----------+
       |          |                   |          |
   Production Inventory            Sales     Maintenance
       |          |                   |          |
   Weighbridge Dispatch          Purchases   Vehicles
```

Backend flow:

```text
API
 ↓
Authentication
 ↓
Authorization
 ↓
Service
 ↓
Repository
 ↓
Database
```

Frontend flow:

```text
Component
 ↓
Facade / State
 ↓
API Service
 ↓
Backend API
```

Do not put core business logic in routers or Angular components.

---

# 5. Multi-Tenancy

The system must support multiple independent companies.

Example:

```text
Platform
├── ABC Stone Crushers
│   ├── Pampore Plant
│   └── Pulwama Plant
├── XYZ Aggregates
│   └── Srinagar Plant
└── Kashmir Construction Materials
    └── Anantnag Plant
```

Tenant A must never access Tenant B data.

Never trust tenant_id supplied by the frontend.

The backend security context must determine the tenant.

Tenant model should include:

```text
id
name
code
slug
status
timezone
currency
created_at
updated_at
```

Statuses:

```text
ACTIVE
SUSPENDED
INACTIVE
```

---

# 6. Organization Hierarchy

Support:

```text
Tenant
 ↓
Business Unit
 ↓
Plant
 ↓
Site
 ↓
Department
```

Not every tenant must use every level.

Future modules must be able to reference organizational scope.

---

# 7. Identity

Create a robust User model:

```text
id
tenant_id
email
password_hash
first_name
last_name
phone
status
is_verified
last_login_at
created_at
updated_at
```

Use Argon2id or another secure password hashing algorithm.

Never store plaintext passwords.

Support:

- Platform-level users
- Tenant-level users
- Account activation/deactivation
- Login history foundation
- Password reset foundation
- Session/token management

---

# 8. Authentication

Implement:

```text
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
```

Use secure access and refresh token handling.

Design so Microsoft Entra ID can be added later.

Do not make Entra ID mandatory unless required by the existing repository.

---

# 9. RBAC

Create:

```text
Role
Permission
UserRole
RolePermission
```

Use stable permission codes:

```text
dashboard.view

users.view
users.create
users.update
users.delete

roles.view
roles.create
roles.update
roles.delete

permissions.view

tenants.view
tenants.create
tenants.update
tenants.delete

settings.view
settings.update

audit.view

documents.view
documents.upload
documents.delete
```

Seed initial roles:

```text
SUPER_ADMIN
TENANT_ADMIN
MANAGER
OPERATOR
ACCOUNTANT
STOREKEEPER
VIEWER
```

Do not rely on database IDs for roles.

---

# 10. Scope-Based Authorization

RBAC answers:

> What can the user do?

Scope answers:

> Where can the user do it?

Example:

```text
Permission: production.update
Scope: Pampore Plant
```

Another:

```text
Permission: production.view
Scope: All Plants
```

Support scopes:

```text
PLATFORM
TENANT
BUSINESS_UNIT
PLANT
SITE
DEPARTMENT
```

Create reusable authorization mechanisms such as:

```text
require_authenticated_user()
require_permission("users.view")
require_permission("users.create")
authorize(permission, resource_scope)
```

Every future module must use this system.

---

# 11. Security Context

Every authenticated request should resolve:

```text
User
Tenant
Roles
Permissions
Organization scope
Plant/site scope
```

Future modules must not implement their own tenant or permission logic.

---

# 12. Tenant Isolation

Mandatory tests:

- Tenant A cannot read Tenant B data.
- Tenant A cannot update Tenant B data.
- Tenant A cannot delete Tenant B data.
- Changing an ID in a request cannot bypass tenant isolation.
- Tenant Admin cannot access another tenant.
- Plant-scoped users cannot access another plant outside their scope.

---

# 13. Database Standards

Use UUIDs for major entities where appropriate.

Important entities normally contain:

```text
id
created_at
updated_at
```

Where appropriate:

```text
created_by
updated_by
```

Use timezone-aware timestamps.

Use PostgreSQL NUMERIC/DECIMAL for money and precision-sensitive quantities.

Never use floating point for money.

---

# 14. Deletion Rules

Do not blindly implement soft-delete everywhere.

Use:

- Active/inactive for master data where appropriate.
- Cancel/reverse/void for important transactions.
- Hard deletion only where safe.

Important operational and financial history must not disappear casually.

---

# 15. Audit

Create an append-only audit system.

Audit event:

```text
id
tenant_id
user_id
action
resource_type
resource_id
old_data
new_data
ip_address
user_agent
request_id
timestamp
```

Record important actions such as:

```text
LOGIN
LOGIN_FAILED
LOGOUT
USER_CREATED
USER_UPDATED
USER_DISABLED
ROLE_CREATED
ROLE_UPDATED
ROLE_DELETED
PERMISSION_CHANGED
TENANT_CREATED
TENANT_UPDATED
TENANT_SUSPENDED
SETTINGS_CHANGED
```

Future modules must be able to create audit events through a shared service.

Normal users must not edit or delete audit history.

---

# 16. Request ID

Every API request should have a correlation/request ID.

Use it in:

- Logs
- Audit
- Errors where appropriate
- Application Insights telemetry

---

# 17. Document Numbering

Create a reusable concurrency-safe document-number service.

Support:

```text
Tenant
Plant
Document Type
Fiscal Year
Prefix
Sequence
```

Examples:

```text
INV-000001
PO-000001
SO-000001
WB-000001
PROD-000001
JOB-000001
```

Example:

```text
PAMP/INV/2026-27/000125
```

Do not let individual modules implement their own numbering.

---

# 18. Fiscal Year

Create a fiscal-year foundation:

```text
FiscalYear
```

Support:

- start_date
- end_date
- code
- active/closed status

Do not hard-code a particular financial year into business logic.

---

# 19. Status / State Foundation

Create a consistent approach for controlled states.

Examples:

```text
DRAFT
SUBMITTED
APPROVED
REJECTED
CANCELLED
COMPLETED
CLOSED
```

Do not allow arbitrary client-side status changes.

Future modules define their own valid transitions.

---

# 20. Workflow / Approval Foundation

Create reusable concepts:

```text
WorkflowDefinition
WorkflowInstance
ApprovalStep
ApprovalAction
```

Support:

```text
Submit
Approve
Reject
Return
Cancel
```

Record:

```text
Who
When
Action
Comment
Previous state
New state
```

Do not build an unnecessarily complex workflow engine.

---

# 21. Attachments / Documents

Create a reusable attachment system.

Metadata:

```text
id
tenant_id
entity_type
entity_id
file_name
content_type
size
storage_key
uploaded_by
created_at
```

Store actual files in Azure Blob Storage.

Create a storage abstraction:

```text
StorageService
 ├── LocalStorageProvider
 └── AzureBlobStorageProvider
```

Methods:

```text
upload
download
delete
generate_access_url
```

---

# 22. Notifications

Create a shared notification service.

Initial channel:

```text
IN_APP
```

Design extension points for:

```text
EMAIL
SMS
PUSH
WHATSAPP
```

Future modules should call the notification service rather than implementing their own notification logic.

---

# 23. Settings

Support:

```text
Platform Settings
 ↓
Tenant Settings
 ↓
Plant Settings
 ↓
Module Settings
```

Examples:

```text
currency
timezone
date_format
weight_unit
tax_configuration
document_numbering
approval_limits
notification_preferences
```

Avoid hard-coded business rules that may vary between tenants.

---

# 24. Units of Measurement

This is important for stone-crusher operations.

Create:

```text
Unit
UnitCategory
UnitConversion
```

Examples:

```text
kg
ton
litre
km
hour
piece
set
```

Support mathematically valid conversions.

Do not assume volume-to-weight conversion is universal; material density may be needed later.

---

# 25. Master Data Framework

Create reusable patterns for:

```text
code
name
description
status
created_at
updated_at
```

Prefer deactivation over deletion when records are referenced.

---

# 26. Location Foundation

Support reusable operational locations:

```text
Plant
Warehouse
Stock Yard
Workshop
Office
Storage Area
```

Future inventory and maintenance modules must be able to reference locations.

---

# 27. Cost Centre / Profit Centre

Create:

```text
CostCentre
ProfitCentre
```

Examples:

```text
Pampore Plant
Crusher Line 1
Workshop
Transport
Administration
```

---

# 28. Transaction vs Balance

Future systems should prefer:

```text
Transaction
 ↓
Ledger
 ↓
Balance / Projection
```

instead of directly modifying balances.

This principle will eventually support:

```text
Inventory Ledger
Fuel Ledger
Vehicle Mileage Ledger
Machine Hours Ledger
Financial Ledger
```

---

# 29. Concurrency

Design for concurrent users.

Use:

- Database transactions
- Unique constraints
- Appropriate locking
- Optimistic concurrency where appropriate
- Idempotency where appropriate

Example: two users must not receive the same document number.

---

# 30. Idempotency

Support idempotency/external references for future integrations.

This is particularly important for:

- Weighbridge
- RFID
- IoT
- GPS
- External APIs

The same external transaction received twice must not create duplicate business transactions.

---

# 31. Event Foundation

Create a lightweight internal event abstraction.

Examples:

```text
UserCreated
TenantCreated
RoleChanged
DocumentUploaded
ApprovalCompleted
```

Future examples:

```text
ProductionCompleted
StockReceived
InvoiceCreated
PaymentReceived
MaintenanceCompleted
```

Do not introduce Kafka/RabbitMQ unless there is a real requirement.

---

# 32. Background Jobs

Design a reusable background-job abstraction.

Future jobs:

```text
Document expiry reminders
Notifications
Report generation
Scheduled maintenance generation
Daily KPI calculations
Data synchronization
```

Do not perform long-running work inside HTTP requests.

---

# 33. API Standards

All APIs use:

```text
/api/v1/
```

Standardize:

- Authentication
- Authorization
- Pagination
- Filtering
- Sorting
- Searching
- Validation
- Errors
- Request ID
- Response conventions

Example error:

```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to perform this action.",
    "request_id": "..."
  }
}
```

Do not expose stack traces in production.

---

# 34. Frontend Foundation

Build reusable:

```text
Core
Shared
Layout
Authentication
Authorization
API
State
UI
```

Reusable UI:

```text
DataTable
Pagination
Search
Filters
Forms
Dialogs
Confirmation
FileUpload
StatusBadge
Toast
LoadingState
ErrorState
EmptyState
```

---

# 35. Frontend Authorization

Implement:

```text
AuthService
AuthGuard
PermissionGuard
HTTP interceptor
Session handling
```

Provide:

```text
hasPermission()
hasAnyPermission()
hasAllPermissions()
```

Frontend authorization is for UX only.

Backend remains the security boundary.

---

# 36. Dashboard

Build only a foundation dashboard.

Platform admin:

```text
Tenants
Users
System health
```

Tenant admin:

```text
Plants
Users
Active users
```

Do not build production/sales/inventory dashboards in the foundation phase.

---

# 37. Observability

Implement:

- Structured logging
- Request IDs
- Error logging
- Health checks
- Readiness checks
- Metrics foundation

Endpoints:

```text
/health
/ready
```

Integrate Azure Application Insights in deployed environments.

---

# 38. Security

Implement appropriate:

- CORS
- Security headers
- Request validation
- Rate-limiting strategy
- Payload-size limits
- File-upload validation
- Authentication failure handling
- Secret management

Local secrets use `.env`.

Never commit `.env`.

Production secrets use Azure Key Vault.

---

# 39. Testing

Create reusable fixtures:

```text
Tenant A
Tenant B
Super Admin
Tenant Admin
Manager
Operator
Viewer
```

Test:

### Authentication
- Valid login
- Invalid password
- Inactive account
- Invalid token
- Expired token

### RBAC
- Permission granted
- Permission denied
- Role assignment
- Multiple roles

### Scope
- Plant-scoped user
- Tenant-scoped user
- Platform-scoped user

### Multi-tenancy
- Cross-tenant read blocked
- Cross-tenant update blocked
- Cross-tenant delete blocked

### Audit
- Important actions generate audit records

### Documents
- Upload
- Access
- Download
- Delete according to policy

Frontend tests should cover:

- Login
- Auth guard
- Permission guard
- Navigation
- User management
- Role management
- Tenant management
- Error handling
- Session expiry

---

# 40. Docker

Provide:

```text
backend/Dockerfile
frontend/Dockerfile
docker-compose.yml
```

Local Docker environment should support:

```text
PostgreSQL
Backend
Frontend
```

Use health checks and proper service dependencies.

---

# 41. Azure

Prepare infrastructure-as-code for:

```text
Resource Group
Azure Container Registry
Azure Database for PostgreSQL
Azure App Service or Container Apps
Azure Key Vault
Storage Account
Application Insights
```

Do not provision real resources without authorization/credentials.

---

# 42. Environments

Support:

```text
Development
Test
Staging
Production
```

Never mix environment secrets/configuration.

---

# 43. CI/CD

Azure DevOps pipeline:

```text
Commit
 ↓
Install dependencies
 ↓
Lint
 ↓
Backend tests
 ↓
Frontend tests
 ↓
Security checks
 ↓
Build
 ↓
Docker build
 ↓
Push image
 ↓
Deploy Development
```

Future promotion:

```text
Development
 ↓
Testing
 ↓
Staging
 ↓
Approval
 ↓
Production
```

Never put credentials directly into YAML.

---

# 44. Database Migration Discipline

All schema changes use Alembic.

Never manually modify production schema and then attempt to reconstruct migrations.

Process:

```text
Model change
 ↓
Migration
 ↓
Test
 ↓
Deploy
```

---

# 45. Backup / Recovery

Document:

- PostgreSQL backups
- Point-in-time recovery
- Blob backup
- RPO
- RTO
- Restore procedure

A production deployment is incomplete without recovery planning.

---

# 46. Documentation

Maintain:

```text
docs/
├── architecture.md
├── database.md
├── authentication.md
├── authorization.md
├── multi-tenancy.md
├── organization.md
├── audit.md
├── workflows.md
├── documents.md
├── notifications.md
├── api.md
├── testing.md
├── azure.md
├── security.md
└── development.md
```

Documentation must reflect actual implementation.

Never document fake functionality as completed.

---

# 47. ADRs

Create Architecture Decision Records:

```text
ADR-001 Monorepo
ADR-002 Multi-tenancy strategy
ADR-003 Authentication strategy
ADR-004 RBAC and scope model
ADR-005 Database ID strategy
ADR-006 File storage strategy
ADR-007 Audit architecture
ADR-008 Workflow architecture
ADR-009 Azure hosting architecture
ADR-010 Background job architecture
```

Each ADR:

```text
Context
Problem
Options
Decision
Reason
Consequences
```

---

# 48. Modular Monolith

Do NOT create microservices initially.

Use a modular monolith with clear module boundaries.

Future modules:

```text
Production
Weighbridge
Inventory
Sales
Dispatch
Purchases
Maintenance
Vehicles
Fuel
Finance
Quality
Safety
Compliance
Reporting
Analytics
```

Each future module must reuse:

- Authentication
- Tenancy
- Organization
- RBAC
- Scope
- Audit
- Workflow
- Documents
- Notifications
- Numbering
- Settings
- Units
- Shared UI
- Shared API conventions

---

# 49. Business Module Contract

Every future module should contain:

```text
Database Models
Migration
Schemas
Repository
Service
API
Permissions
Scope Rules
Audit Events
Notifications
Workflow
Attachments
Tests
Frontend
Documentation
```

A business module must not create its own authentication, tenancy or permission engine.

---

# 50. What NOT to Build in Foundation

Do not implement:

```text
Production
Weighbridge
Raw Material Receiving
Inventory
Sales
Dispatch
Purchases
Vehicles
Drivers
Machines
Maintenance
Fuel
Expenses
Quality
Safety
Compliance
Profitability
Advanced Reports
```

Only create extension points where useful.

---

# 51. PHASE PLAN

Use the following phase sequence.

## PHASE 0 — Platform Foundation

Build:

- Repository/monorepo
- Backend architecture
- Frontend architecture
- PostgreSQL
- Alembic
- Authentication
- Users
- Tenants
- Organization hierarchy
- RBAC
- Permissions
- Scope-based access
- Tenant isolation
- Audit
- Request IDs
- Document numbering
- Fiscal year foundation
- State foundation
- Workflow foundation
- Attachments
- Blob storage abstraction
- Notifications foundation
- Settings
- Units
- Locations
- Cost centres
- Profit centres
- Event abstraction
- Background job abstraction
- Shared frontend components
- Docker
- Testing foundation
- Logging
- Health checks
- Azure infrastructure foundation
- Azure DevOps CI/CD
- Documentation
- ADRs

### Phase 0 Definition of Done

Do not declare complete until:

- App runs locally.
- Database migrations work.
- Authentication works.
- Tenant creation works.
- Multiple tenants work.
- Tenant isolation tests pass.
- RBAC works.
- Scope authorization works.
- Audit works.
- Frontend authentication works.
- Frontend permission guards work.
- Shared UI exists.
- Docker works.
- Backend tests pass.
- Frontend tests pass.
- Lint passes.
- Build passes.
- CI pipeline passes.
- Azure deployment path is documented/tested as available.
- Documentation matches implementation.

---

# PHASE 1 — Master Data Foundation

After Phase 0 is accepted, build the reusable master-data layer.

Examples:

```text
Plants
Sites
Departments
Materials
Material Categories
Products
Product Categories
Customers
Suppliers
Employees
Vehicles
Drivers
Machines
Equipment
Locations
Units
Tax Codes
Payment Terms
Cost Centres
Profit Centres
```

Important:

Master data should be tenant-aware and scope-aware where appropriate.

Use common patterns.

Do not duplicate CRUD architecture.

---

# PHASE 2 — Weighbridge + Raw Material

Build:

```text
Weighbridge Tickets
Vehicle Entry
Vehicle Exit
Gross Weight
Tare Weight
Net Weight
Material
Supplier
Customer
Driver
Gate
External Reference
Ticket Status
```

Must support:

- Duplicate prevention
- Audit
- Scope
- Tenant isolation
- Attachments
- Numbering
- Reports foundation

---

# PHASE 3 — Production

Build:

```text
Production Plans
Production Runs
Crusher Lines
Input Material
Output Material
Production Quantity
Shift
Operator
Machine
Downtime
Production Status
```

Use the platform's:

- Permissions
- Scope
- Units
- Numbering
- Audit
- Workflow
- Notifications
- Events

---

# PHASE 4 — Inventory

Build:

```text
Warehouses
Stock Yards
Bins/Locations
Stock Receipts
Stock Issues
Transfers
Adjustments
Stock Ledger
Stock Balance
Minimum Stock
Reorder Level
```

Do not directly manipulate stock balances without transaction records.

---

# PHASE 5 — Sales + Dispatch

Build:

```text
Customers
Quotations
Sales Orders
Invoices
Dispatch Orders
Delivery
Vehicle Assignment
Weighbridge Link
Payment Status
```

Use document numbering, workflow, audit and approvals.

---

# PHASE 6 — Purchases + Expenses

Build:

```text
Purchase Requests
Approvals
Purchase Orders
Goods Receipts
Supplier Invoices
Expenses
Expense Categories
Approvals
Cost Centre Allocation
```

---

# PHASE 7 — Maintenance + Machinery

Build:

```text
Machines
Assets
Maintenance Plans
Preventive Maintenance
Breakdown
Work Orders
Parts
Service History
Downtime
Machine Hours
```

---

# PHASE 8 — Vehicles + Fuel

Build:

```text
Vehicles
Drivers
Vehicle Assignments
Fuel
Fuel Transactions
Mileage
Trips
Vehicle Documents
Insurance
Fitness
Permit
Service
```

---

# PHASE 9 — Finance

Integrate/extend:

```text
Accounts
Receivables
Payables
Payments
Expenses
Cost Centres
Profit Centres
Tax
Financial Reporting
```

Prefer integration with external accounting systems where appropriate instead of recreating a full accounting ERP unnecessarily.

---

# PHASE 10 — Quality / Safety / Compliance

Build:

```text
Quality Tests
Material Quality
Safety Incidents
Inspections
Compliance Documents
Expiry Tracking
Corrective Actions
Approvals
```

---

# PHASE 11 — Reporting / Analytics

Build:

```text
Production Dashboard
Sales Dashboard
Inventory Dashboard
Weighbridge Dashboard
Maintenance Dashboard
Vehicle Dashboard
Financial Dashboard
Management Dashboard
```

Support:

- Date filtering
- Plant filtering
- Tenant filtering
- Export
- Excel
- CSV
- PDF where appropriate

---

# 52. HOW TO WORK PHASE BY PHASE

This is extremely important.

DO NOT attempt all phases in one implementation.

Complete exactly one phase at a time.

For each phase:

```text
1. Read the Master Build Specification.
2. Read the current repository.
3. Read previous phase documentation.
4. Inspect current implementation.
5. Identify reusable foundation components.
6. Produce a phase implementation plan.
7. Implement incrementally.
8. Add migrations.
9. Add backend tests.
10. Add frontend tests.
11. Add authorization tests.
12. Add tenant isolation tests where relevant.
13. Add audit coverage.
14. Add documentation.
15. Run lint.
16. Run backend tests.
17. Run frontend tests.
18. Run builds.
19. Review security.
20. Review database integrity.
21. Review API consistency.
22. Review frontend consistency.
23. Provide a phase completion report.
24. STOP.
```

Do not automatically start the next phase.

---

# 53. CONTINUATION PROTOCOL

After a phase is completed, I will start a new Claude conversation/session if necessary.

When I say:

> CONTINUE TO NEXT PHASE

you must:

1. Read this master file.
2. Inspect the actual repository.
3. Determine which phases are complete.
4. Read the phase completion report.
5. Identify the next incomplete phase.
6. Do not rebuild completed work.
7. Do not assume documentation is correct if code contradicts it.
8. Verify the actual code.
9. Create the next phase implementation plan.
10. Implement only that phase.
11. Run all regression tests.
12. Stop after completing that phase.

If I say:

> CONTINUE PHASE 1

work only on Phase 1.

If I say:

> AUDIT CURRENT STATE

do not implement anything initially. Inspect the repository and report:

```text
Completed
Partially completed
Missing
Incorrect
Security risks
Technical debt
Tests missing
Documentation missing
Recommended next action
```

---

# 54. PHASE COMPLETION REPORT

At the end of every phase, create/update:

```text
docs/phases/phase-X-completion.md
```

Use:

```text
# Phase X Completion

## Objective

## Implemented

## Database Changes

## API Changes

## Frontend Changes

## Permissions Added

## Scope Rules

## Audit Events

## Notifications

## Tests

## Security Verification

## CI/CD Verification

## Documentation Updated

## Known Limitations

## Technical Debt

## Files Changed

## Migration IDs

## Next Phase

## Explicitly NOT Implemented
```

---

# 55. GIT / COMMIT DISCIPLINE

Use meaningful commits.

Examples:

```text
feat(platform): add tenant foundation
feat(auth): add authentication
feat(authz): add RBAC and permission scopes
feat(audit): add audit event system
feat(storage): add blob storage abstraction
feat(master-data): add plant and material masters
test(authz): add tenant isolation tests
docs(platform): update architecture
```

Do not mix unrelated changes in one commit where avoidable.

---

# 56. NEVER CLAIM COMPLETION WITHOUT EVIDENCE

Claude must not say:

> "Implemented successfully"

unless it actually:

- changed the code,
- ran relevant tests,
- checked migration status,
- checked build,
- checked lint where applicable,
- and verified the result.

If something cannot be tested because credentials/infrastructure are unavailable, explicitly say so.

---

# 57. START INSTRUCTION

When this file is first given to Claude:

DO NOT immediately implement all phases.

Start with:

```text
PHASE 0 — STEP 1
Repository inspection and architecture assessment.
```

Report:

1. Current repository structure.
2. Existing technologies.
3. Existing backend.
4. Existing frontend.
5. Existing database.
6. Existing infrastructure.
7. Existing CI/CD.
8. Existing tests.
9. Conflicts with this specification.
10. Recommended Phase 0 implementation plan.

Then proceed incrementally.

---

# 58. FINAL PRODUCT VISION

The final platform should look conceptually like:

```text
                    STONE CRUSHER PLATFORM
                              |
        +---------------------+---------------------+
        |                     |                     |
     Identity              Tenancy             Organization
        |                     |                     |
        +---------------------+---------------------+
                              |
                         RBAC + Scope
                              |
        +----------+----------+----------+-----------+
        |          |                     |           |
      Audit     Workflow             Documents   Settings
        |          |                     |           |
        +----------+----------+----------+-----------+
                              |
                    Shared Platform Services
                              |
    +-----------+-------------+-------------+-----------+
    |           |             |             |           |
Weighbridge Production     Inventory      Sales     Maintenance
    |           |             |             |           |
    +-----------+-------------+-------------+-----------+
                              |
                   Purchases / Vehicles / Fuel
                              |
                    Finance / Quality / Safety
                              |
                     Reports / Analytics
```

The foundation must remain stable while business modules grow around it.

The guiding principle is:

> Build the platform once. Add business modules without rebuilding the platform.
