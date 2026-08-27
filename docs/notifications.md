# Notifications

`app/models/notification.py`'s module docstring states the scope plainly: "Only IN_APP is
delivered in Phase 0; other channels are extension points implemented by future channel providers
registered with NotificationService." This document is precise about what that split actually
means in the code today.

## The model

**`Notification`** (`app/models/notification.py`): `tenant_id` (nullable — a platform-level
notification isn't scoped to one tenant), `user_id` (required — every notification belongs to
exactly one recipient), `channel` (a real Postgres enum, `NotificationChannel`, default
`IN_APP`), `title` and `body`, an optional `entity_type` + `entity_id` pair (the same generic
pattern used by `Attachment`, `AuditEvent`, and `WorkflowInstance`, letting a notification point
back at whatever business record triggered it), and read tracking via `is_read` (default `False`)
and a nullable `read_at` timestamp.

There is exactly one table for all channels — `channel` is a column on `Notification`, not a
separate delivery-log table per channel. That's a deliberate simplification: today, every
`Notification` row *is* the delivered IN_APP notification (its existence in the table is the
delivery), while for a not-yet-implemented channel the same row would represent a delivery
request that a future channel provider consumes and dispatches externally.

## The service

`app/services/notification_service.py` is the single entry point business logic is expected to
use — its docstring is direct: "Future business modules should call `send()` rather than writing
directly to the notifications table." Three functions, and this is the entire service:

- **`send()`** — creates a `Notification` row (`channel` defaults to `IN_APP` if the caller
  doesn't specify one) and commits. That's it — there's no branch on `channel`, no dispatch to an
  external provider, no queue. Writing the row *is* the entire implementation of `send()`,
  regardless of which channel value is passed.
- **`list_for_user()`** — paginated list of a user's notifications, with an `unread_only` filter.
- **`mark_read()`** — loads the notification scoped to the requesting user
  (`notification_repository.get_for_user()`, so a user can't mark someone else's notification
  read), flips `is_read`/`read_at` via `notification_repository.mark_read()`, and commits.

`GET /api/v1/notifications` and `POST /api/v1/notifications/{id}/read`
(`app/api/v1/notifications.py`) expose exactly these two read operations, both scoped to
`context.user.id` from the authenticated caller — there's no endpoint to create a notification
directly; that only happens from within other services calling `send()`.

## What's actually delivered vs. what's an extension point

The docstring's phrase "registered with NotificationService" describes an intended future
architecture, not something present in the code today — there is no channel-provider registry,
no interface for one, and no per-channel dispatch logic anywhere in
`notification_service.py`. Being precise about the four non-IN_APP values in
`NotificationChannel`:

```python
class NotificationChannel(enum.StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WHATSAPP = "WHATSAPP"
```

- **`IN_APP`** — fully implemented and delivered. A `Notification` row is created, and the
  authenticated user retrieves it through the two API routes above. This is the only channel with
  an actual delivery mechanism in Phase 0.
- **`EMAIL`** — zero implementation in `notification_service.py`. It exists as an enum value a
  caller could pass to `send()` today, which would just create a `Notification` row with
  `channel=EMAIL` and never actually email anyone — nothing reads that row and dispatches an
  email. The one concrete reference to this gap in the codebase is a comment in
  `auth_service.request_password_reset()`: "Phase 0 does not deliver email; the raw token would
  be dispatched via the notification service's EMAIL channel extension point once implemented."
  Consistent with that, the password reset flow does not call `notification_service.send()` at
  all today — it logs the raw token at debug level in non-production instead, precisely because
  there is no working delivery path to hand it to.
- **`SMS`**, **`PUSH`**, **`WHATSAPP`** — same status as EMAIL: enum values with zero
  implementation anywhere. No service, no provider stub, no code path references them outside the
  enum declaration itself.

So the accurate summary is: one channel (IN_APP) end-to-end; four channel identifiers reserved in
the type system for future work, none of which have so much as a stub provider yet. Nothing in the
current code partially implements EMAIL/SMS/PUSH/WHATSAPP — they are placeholders in the enum only,
present so that a future channel provider can be registered against an existing, stable channel
name instead of requiring a schema migration to introduce it.
