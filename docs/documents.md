# Documents: Numbering, Attachments, Storage, and Fiscal Year

Four related pieces of shared infrastructure exist so that future business documents (purchase
orders, dispatch notes, weighbridge tickets, invoices, and so on) don't each reinvent numbering,
file handling, or the concept of a financial year: document numbering (`DocumentSequence` +
`numbering_service`), attachment metadata (`Attachment` + `attachment_service`), blob storage
(`storage_service`), and `FiscalYear` as a shared reference concept. None of these are business
documents themselves — they're the plumbing a later business module is expected to call into.

## Document numbering

**Model — `DocumentSequence`** (`app/models/numbering.py`): one row per
`(tenant_id, organization_unit_id, document_type, fiscal_year_code)`, enforced by a unique
constraint (`uq_document_sequence_scope`). Each row holds a `prefix` string, a `last_sequence`
integer counter (starts at 0), and a `padding` width (default 6) used to zero-pad the number.
`organization_unit_id` is nullable, so a sequence can be scoped tenant-wide or narrowed to one
organization unit, depending on how a given document type needs to number things.

**Service — `numbering_service.next_number()`** (`app/services/numbering_service.py`) is the only
way a business module is meant to generate a document number; the module docstring says outright:
"Individual business modules must call this service instead of implementing their own numbering."

The mechanism, read directly from the code:

1. Look up the `DocumentSequence` row for the given `(tenant_id, organization_unit_id,
   document_type, fiscal_year_code)`.
2. If it doesn't exist yet, create it (`last_sequence=0`) and flush. This is the one place a race
   is possible — two concurrent first-ever requests for the same scope could both try to insert —
   but the code accepts that: the unique constraint on `DocumentSequence` rejects the second
   INSERT rather than silently allocating a duplicate sequence. The comment in the code is explicit
   that this is acceptable because it's "a rare, one-time-per-scope event (not the hot path)", so
   failing loud and letting the caller retry beats adding locking complexity for a case that
   happens once per scope, ever.
3. For every call after the row exists (the hot path), issue a single atomic statement:
   `UPDATE document_sequences SET last_sequence = last_sequence + 1 WHERE id = ... RETURNING
   last_sequence, prefix, padding`. PostgreSQL guarantees this single-statement
   read-modify-write is atomic per row under the default READ COMMITTED isolation level, so two
   concurrent callers racing for the same scope can never observe or receive the same number — no
   explicit `SELECT ... FOR UPDATE` or custom locking is needed.
4. Format the result as `f"{prefix}-{str(new_sequence).zfill(padding)}"` and commit.

So a document number is always `PREFIX-000123`-shaped: a caller-supplied prefix, a literal hyphen,
and the running sequence zero-padded to `padding` digits (6 by default, e.g. `PO-000001`). The
`fiscal_year_code` is a plain string parameter to `next_number()` — the service does not look it
up from the `FiscalYear` table itself; the caller decides which fiscal year code the sequence
belongs to (see below).

## Attachments

**Model — `Attachment`** (`app/models/attachment.py`): metadata only — "Actual bytes live in blob
storage" per its docstring. Fields: `tenant_id`, the generic `entity_type` + `entity_id` pair (the
same pattern as `AuditEvent` and `WorkflowInstance`, letting an attachment point at any future
business record without a hard foreign key into that module's table), `file_name`,
`content_type`, `size` (`BigInteger`, so large files aren't a problem at the schema level),
`storage_key` (unique — the opaque handle into blob storage), and `uploaded_by`.

**Service — `attachment_service.py`** enforces the actual rules on top of that model
(Master Build Specification sections 21 and 39):

- **Tenant isolation**: every operation requires `context.tenant_id` — attachments cannot be
  created or read outside a tenant context (`ValidationAppError("Attachments require a tenant
  context.")`).
- **Size limit**: `upload()` rejects any payload larger than `settings.max_upload_size_mb` (25MB
  by default, configurable via `MAX_UPLOAD_SIZE_MB`).
- **Permission gate on delete**: enforced at the route layer — `DELETE
  /api/v1/attachments/{id}` requires `documents.delete`, upload requires `documents.upload`, and
  read/list require `documents.view` (`app/api/v1/attachments.py`).
- **Audit**: both `upload()` and `delete()` call `audit_service.record()` — `"DOCUMENT_UPLOADED"`
  with `new_data` describing the file, entity type, and entity id; `"DOCUMENT_DELETED"` with
  `old_data` describing the file name. These are literal action strings, not (yet) members of
  `AuditAction`.
- **Ownership check**: `get_download_url()` and `delete()` both go through `_get_owned()`, which
  loads the attachment scoped to `context.tenant_id` via
  `attachment_repository.get_by_id_in_tenant()` — an attachment from another tenant simply
  doesn't resolve (`NotFoundError`), it isn't a 403.

`upload()` builds the storage key via `storage_service.build_storage_key()` *before* creating the
`Attachment` row, uploads through the active storage provider, and only then persists metadata —
so a failed upload never leaves an orphaned `Attachment` row pointing at nonexistent bytes.

## Storage abstraction

`app/services/storage_service.py` is a small provider abstraction, described in its own docstring
diagram:

```
StorageService
 ├── LocalStorageProvider    (default outside production; writes under LOCAL_STORAGE_PATH)
 └── AzureBlobStorageProvider (used when STORAGE_PROVIDER=azure)
```

Both implement the same `StorageProvider` ABC — `upload`, `download`, `delete`,
`generate_access_url` — and `attachment_service.py` depends only on that protocol, never on a
concrete class, so switching providers is "a configuration change, not a code change" (the
module's own words). The active provider is chosen once, lazily, and cached in a module-level
`_provider` singleton by `get_storage_provider()`, based on `settings.storage_provider` (a
`Literal["local", "azure"]` in `app/core/config.py`, defaulting to `"local"`).

**`LocalStorageProvider`** — "Suitable for local development only" per its own docstring. Writes
files under `LOCAL_STORAGE_PATH` (default `./storage`). `_resolve()` defends against path
traversal from a malicious `storage_key` by stripping `..` sequences and verifying the resolved
absolute path is actually inside the configured base path before touching the filesystem. Because
there's no public URL to hand out locally, `generate_access_url()` returns an internal API path
(`/api/v1/attachments/local/{key}`) rather than a real signed URL — the download endpoint is
expected to serve the bytes itself in this mode.

**`AzureBlobStorageProvider`** — used when `STORAGE_PROVIDER=azure`, backed by
`azure-storage-blob`'s async client, configured via `AZURE_STORAGE_CONNECTION_STRING` and
`AZURE_STORAGE_CONTAINER` (default container name `"attachments"`). `upload()` sets the blob's
`ContentSettings` from the attachment's `content_type` and overwrites unconditionally. Unlike the
local provider, `generate_access_url()` here returns a real, time-limited SAS URL
(`generate_blob_sas` with `BlobSasPermissions(read=True)`, default 3600-second expiry) — a caller
can hand this URL directly to a client for a temporary, unauthenticated download rather than
proxying bytes through the API.

**`build_storage_key()`** constructs the key every provider ultimately stores under:
`f"{tenant_id}/{entity_type}/{entity_id}/{unique_suffix}_{safe_name}"`, where `unique_suffix` is
12 hex characters from a fresh UUID4. The tenant/entity_type/entity_id prefix keeps files
logically grouped per business record (and trivially lets you reason about which tenant a blob
belongs to just from its key); the random suffix means two uploads of a file with the same name
never collide.

## Fiscal year

**Model — `FiscalYear`** (`app/models/fiscal_year.py`): "A tenant's financial year. No business
logic anywhere may hard-code a particular year" per its own docstring. Fields are a `code`
(free-form string, e.g. `"2026-27"`), `start_date`/`end_date`, and two independent booleans:
`is_active` (the fiscal year currently in effect for day-to-day operations) and `is_closed`
(a fiscal year that's been locked against further posting — a book-keeping distinction separate
from "active"). `(tenant_id, code)` is unique per tenant.

**Relationship to numbering**: conceptual, not a foreign key. `DocumentSequence.fiscal_year_code`
and `numbering_service.next_number(..., fiscal_year_code=...)` both take a plain string, not a
reference to `FiscalYear.id`. There is currently no service or API route for `FiscalYear` itself
(no `fiscal_year_service.py`, no `/api/v1/fiscal-years` route) — only the model exists in Phase 0.
The expectation is that once a fiscal year is managed through a real service, callers of
`next_number()` will source `fiscal_year_code` from the tenant's active `FiscalYear.code` rather
than a hard-coded literal, which is exactly the discipline the model's docstring is asking for
("No business logic anywhere may hard-code a particular year") — but that wiring doesn't exist
yet, and this document is not claiming otherwise.
