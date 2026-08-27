# Workflow / Approval Foundation

`app/models/workflow.py` implements the lightweight approval foundation described in Master Build
Specification section 20. Its own module docstring sets the scope deliberately narrow: "a
WorkflowDefinition owns an ordered list of WorkflowStepDefinitions; when a business document needs
approval, the owning service creates a WorkflowInstance and records every
Submit/Approve/Reject/Return/Cancel as an ApprovalAction (who, when, action, comment, previous
state, new state). This is not a general-purpose BPMN engine by design."

That constraint is the point: there is no conditional branching, no parallel approval paths, no
timers or escalation rules, and no workflow-definition editor. What exists is a small, fixed
vocabulary of linear approval steps that a future business module can attach itself to without the
platform needing to understand what that module's documents actually are.

## The four models

**`WorkflowDefinition`** — the template. Identifies a workflow by `code` and human-readable
`name`, scoped to a `tenant_id` (nullable, so a definition can be platform-provided and shared
across tenants) and an `entity_type` string (e.g. what kind of business document this definition
applies to — a purchase order, a dispatch note, whatever a later phase introduces). `is_active`
lets a definition be retired without deleting history that already references it.

**`WorkflowStepDefinition`** — one ordered step within a definition. Each row belongs to exactly
one `WorkflowDefinition` (`workflow_definition_id`, cascade-deleted with it), carries a
`sequence_order` integer that fixes its position in the approval chain, a `name`, and an optional
`required_permission` — the permission string a user must hold to act at this step. This is how
"who can approve step 2" is expressed: not as a role assignment on the step itself, but as a
permission check delegated to the platform's existing RBAC system.

**`WorkflowInstance`** — the running approval for one specific business document. It points at
its `WorkflowDefinition` (`ondelete="RESTRICT"` — a definition can't be deleted while instances
still reference it) and identifies the document it's tracking via `entity_type` + `entity_id`
(the same string-pair pattern used by `Attachment` and `AuditEvent`, so workflow instances,
attachments, and audit events can all point at the same business record without the platform
needing a foreign key into every future module's tables). Two fields carry the live state:
`current_state` (defaults to `"DRAFT"`) and `current_step_order` (defaults to `0`, i.e. before the
first step). `tenant_id` is required here (unlike on the definition) because a running instance
always belongs to exactly one tenant's document.

**`ApprovalAction`** — the audit trail of the approval process itself: one row per
Submit/Approve/Reject/Return/Cancel. Each action records which `WorkflowInstance` it belongs to,
the `step_order` it occurred at (nullable — a `CANCEL` may not be tied to a specific step), the
`action` (a real `WorkflowAction` enum, backed by a Postgres enum type `workflow_action`, unlike
`AuditEvent.action` which is a plain string), the `actor_user_id`, an optional free-text
`comment`, and — critically — both `previous_state` and `new_state`. Storing the state transition
on the action itself, rather than only updating `WorkflowInstance.current_state` in place, means
the full history of state changes survives even though the instance only ever shows its current
state.

## How they relate

```
WorkflowDefinition  1 ──── * WorkflowStepDefinition   (the template: ordered steps)
WorkflowDefinition  1 ──── * WorkflowInstance          (one instance per approved document)
WorkflowInstance    1 ──── * ApprovalAction            (the history of what happened to it)
```

A business document's lifecycle under this model looks like: a service creates a
`WorkflowInstance` against the right `WorkflowDefinition` when the document needs approval
(`current_state="DRAFT"`, `current_step_order=0`). Submitting the document records a `SUBMIT`
`ApprovalAction` (`previous_state="DRAFT"`, `new_state="SUBMITTED"`) and advances
`current_step_order`. Each subsequent `APPROVE` checks the actor against the relevant
`WorkflowStepDefinition.required_permission`, records the action, and either advances to the next
step or, if it was the last step, moves the instance to a terminal approved state. A `REJECT` or
`RETURN` records the action and moves the instance backward or to a terminal rejected state; a
`CANCEL` can end it at any point. In every case, the instance's `current_state` /
`current_step_order` reflect only where things stand right now, while the full sequence of
`ApprovalAction` rows is the auditable record of how it got there.

## Enum vocabulary

`app/models/enums.py` defines the two enums this model depends on:

```python
class WorkflowAction(enum.StrEnum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN = "RETURN"
    CANCEL = "CANCEL"
```

This is the fixed, five-member action vocabulary referenced above — `ApprovalAction.action` can
only ever be one of these.

```python
class RecordStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
```

`RecordStatus` is the shared state vocabulary for `WorkflowInstance.current_state` and
`ApprovalAction.previous_state` / `new_state` (both stored as plain strings, not a DB enum, so a
future module isn't hard-blocked from introducing a state this shared list doesn't yet name). Its
own docstring is explicit about scope: it "only fixes the shared set of names so status values are
consistent platform-wide" — individual business modules define their own transition rules (which
states can move to which) on top of this shared vocabulary; the model layer doesn't enforce a
state machine.

## Phase 0 scope

This is the foundation only. As of Phase 0, no business module creates a `WorkflowDefinition`,
seeds `WorkflowStepDefinition` rows, or opens a `WorkflowInstance` — there is no
`workflow_service.py` and no `/api/v1/workflow*` route yet, only the four SQLAlchemy models
described above. That's expected, not a gap: Phase 0 is platform foundation (identity, tenancy,
RBAC, audit, numbering, attachments, notifications, and this approval scaffold), and business
documents that actually need approval (purchase orders, dispatch notes, etc.) arrive in later
phases per the phase plan in the README. When those modules land, they're expected to create their
own `WorkflowDefinition`/`WorkflowStepDefinition` rows and drive `WorkflowInstance` /
`ApprovalAction` through a service layer that doesn't exist yet — this document describes the
shape they'll build against, not a feature that's already wired end-to-end.
