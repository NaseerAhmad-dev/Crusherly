"""Background-job abstraction (Master Build Specification section 32).

No long-running work belongs inside an HTTP request. Phase 0 ships the abstraction and a
registry; it does not wire up a production task queue, since there is no real recurring job yet
(document expiry reminders, notification fan-out, report generation, scheduled maintenance
generation, daily KPI calculations, and data synchronization are all listed as FUTURE jobs in the
spec, not Phase 0 deliverables). When the first real job is needed, register it with `@job(...)`
and drive it with FastAPI's `BackgroundTasks` for fire-and-forget work, or wire APScheduler/Celery
behind the same `Job` interface for recurring/durable work — call sites do not change either way.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger("app.jobs")

JobFunc = Callable[..., Awaitable[None]]


@dataclass
class Job:
    name: str
    func: JobFunc


_registry: dict[str, Job] = {}


def job(name: str):
    """Decorator registering an async function as a named background job."""

    def _wrap(func: JobFunc) -> JobFunc:
        _registry[name] = Job(name=name, func=func)
        return func

    return _wrap


def get_job(name: str) -> Job | None:
    return _registry.get(name)


async def run_job(name: str, *args, **kwargs) -> None:
    registered = get_job(name)
    if registered is None:
        raise ValueError(f"No job registered with name '{name}'.")
    logger.info("Starting background job '%s'", name)
    try:
        await registered.func(*args, **kwargs)
    except Exception:
        logger.exception("Background job '%s' failed", name)
        raise
    else:
        logger.info("Completed background job '%s'", name)
