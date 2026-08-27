"""A lightweight, in-process event bus (Master Build Specification section 31).

Deliberately NOT Kafka/RabbitMQ: there is no real requirement for cross-process messaging yet.
Handlers run in-process, synchronously, right after the publishing transaction commits (callers
publish from services, after `session.commit()`). If a genuine need for durable/cross-process
events shows up in a later phase, this module's `publish`/`subscribe` signatures are the seam to
swap in a real broker without touching call sites.
"""

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

Handler = Callable[[Any], Awaitable[None]]


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events. Subclass with a frozen dataclass per event type."""


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            await handler(event)


event_bus = EventBus()
