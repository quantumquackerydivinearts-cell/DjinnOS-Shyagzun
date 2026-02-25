from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet


ROLE_APPRENTICE = "apprentice"
ROLE_ARTISAN = "artisan"
ROLE_SENIOR_ARTISAN = "senior_artisan"
ROLE_STEWARD = "steward"


@dataclass(frozen=True)
class RoleContext:
    role: str


ROLE_CAPABILITIES: Dict[str, FrozenSet[str]] = {
    ROLE_APPRENTICE: frozenset(
        {
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "crm.contacts.read",
            "booking.read",
            "lesson.read",
            "module.read",
            "lead.read",
            "client.read",
            "quote.read",
            "order.read",
            "inventory.read",
            "supplier.read",
        }
    ),
    ROLE_ARTISAN: frozenset(
        {
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "crm.contacts.read",
            "crm.contacts.write",
            "booking.read",
            "lesson.read",
            "lesson.write",
            "module.read",
            "module.write",
            "lead.read",
            "lead.write",
            "client.read",
            "client.write",
            "quote.read",
            "quote.write",
            "order.read",
            "inventory.read",
            "inventory.write",
            "supplier.read",
            "supplier.write",
        }
    ),
    ROLE_SENIOR_ARTISAN: frozenset(
        {
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
            "crm.contacts.read",
            "crm.contacts.write",
            "booking.read",
            "booking.write",
            "lesson.read",
            "lesson.write",
            "module.read",
            "module.write",
            "lead.read",
            "lead.write",
            "client.read",
            "client.write",
            "quote.read",
            "quote.write",
            "order.read",
            "order.write",
            "inventory.read",
            "inventory.write",
            "supplier.read",
            "supplier.write",
        }
    ),
    ROLE_STEWARD: frozenset(
        {
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
            "crm.contacts.read",
            "crm.contacts.write",
            "booking.read",
            "booking.write",
            "lesson.read",
            "lesson.write",
            "module.read",
            "module.write",
            "lead.read",
            "lead.write",
            "client.read",
            "client.write",
            "quote.read",
            "quote.write",
            "order.read",
            "order.write",
            "inventory.read",
            "inventory.write",
            "supplier.read",
            "supplier.write",
        }
    ),
}


def role_allows(role: str, capability: str) -> bool:
    allowed = ROLE_CAPABILITIES.get(role)
    if allowed is None:
        return False
    return capability in allowed
