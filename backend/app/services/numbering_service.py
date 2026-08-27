"""Concurrency-safe document numbering (Master Build Specification sections 17 and 29).

`next_number()` performs a single atomic `UPDATE ... SET last_sequence = last_sequence + 1
RETURNING last_sequence`. PostgreSQL guarantees this statement is atomic per row, so two
concurrent callers racing for the same (tenant, organization unit, document_type, fiscal_year)
sequence can never observe or return the same number — no explicit row lock or transaction
isolation tuning is needed beyond the default READ COMMITTED.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.numbering import DocumentSequence


async def next_number(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    document_type: str,
    fiscal_year_code: str,
    prefix: str,
    organization_unit_id: uuid.UUID | None = None,
    padding: int = 6,
) -> str:
    existing = await session.execute(
        select(DocumentSequence).where(
            DocumentSequence.tenant_id == tenant_id,
            DocumentSequence.organization_unit_id == organization_unit_id,
            DocumentSequence.document_type == document_type,
            DocumentSequence.fiscal_year_code == fiscal_year_code,
        )
    )
    sequence_row = existing.scalar_one_or_none()

    if sequence_row is None:
        # First document of this (tenant, org unit, type, fiscal year) combination: create the
        # counter row. If two requests race here, the unique constraint on DocumentSequence
        # rejects the second INSERT rather than silently allocating a duplicate sequence — this
        # is a rare, one-time-per-scope event (not the hot path), so failing loud and letting the
        # caller retry is preferable to added locking complexity.
        sequence_row = DocumentSequence(
            tenant_id=tenant_id,
            organization_unit_id=organization_unit_id,
            document_type=document_type,
            fiscal_year_code=fiscal_year_code,
            prefix=prefix,
            last_sequence=0,
            padding=padding,
        )
        session.add(sequence_row)
        await session.flush()

    result = await session.execute(
        update(DocumentSequence)
        .where(DocumentSequence.id == sequence_row.id)
        .values(last_sequence=DocumentSequence.last_sequence + 1)
        .returning(
            DocumentSequence.last_sequence, DocumentSequence.prefix, DocumentSequence.padding
        )
    )
    new_sequence, resolved_prefix, resolved_padding = result.one()
    await session.commit()

    return f"{resolved_prefix}-{str(new_sequence).zfill(resolved_padding)}"
