from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet


ROLE_CLIENT = "client"
ROLE_APPRENTICE = "apprentice"
ROLE_ARTISAN = "artisan"
ROLE_SENIOR_ARTISAN = "senior_artisan"
ROLE_STEWARD = "steward"


@dataclass(frozen=True)
class RoleContext:
    role: str


ROLE_CAPABILITIES: Dict[str, FrozenSet[str]] = {
    ROLE_CLIENT: frozenset(
        {
            "order.read",
            "conversation.read",
            "conversation.write",
            "conversation.create",
        }
    ),
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
            "character.read",
            "quest.read",
            "journal.read",
            "layer.read",
            "function.read",
            "scene.read",
            "shop.read",
            "contract.read",
        }
    ),
    ROLE_ARTISAN: frozenset(
        {
            "conversation.read",
            "conversation.write",
            "conversation.create",
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
            "character.read",
            "character.write",
            "quest.read",
            "quest.write",
            "journal.read",
            "journal.write",
            "layer.read",
            "layer.write",
            "function.read",
            "function.write",
            "scene.read",
            "scene.write",
            "shop.read",
            "shop.write",
            "contract.read",
            "contract.write",
        }
    ),
    ROLE_SENIOR_ARTISAN: frozenset(
        {
            "conversation.read",
            "conversation.write",
            "conversation.create",
            "conversation.admin",
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
            "kernel.interpret",
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
            "character.read",
            "character.write",
            "quest.read",
            "quest.write",
            "journal.read",
            "journal.write",
            "layer.read",
            "layer.write",
            "function.read",
            "function.write",
            "scene.read",
            "scene.write",
            "shop.read",
            "shop.write",
            "contract.read",
            "contract.write",
        }
    ),
    ROLE_STEWARD: frozenset(
        {
            "conversation.read",
            "conversation.write",
            "conversation.create",
            "conversation.admin",
            "kernel.place",
            "kernel.observe",
            "kernel.timeline",
            "kernel.frontiers",
            "kernel.edges",
            "kernel.attest",
            "kernel.interpret",
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
            "character.read",
            "character.write",
            "quest.read",
            "quest.write",
            "journal.read",
            "journal.write",
            "layer.read",
            "layer.write",
            "function.read",
            "function.write",
            "scene.read",
            "scene.write",
            "shop.read",
            "shop.write",
            "shop.admin",
            "ledger.read",
            "ledger.write",
            "contract.read",
            "contract.write",
            "contract.admin",
        }
    ),
}


def role_allows(role: str, capability: str) -> bool:
    allowed = ROLE_CAPABILITIES.get(role)
    if allowed is None:
        return False
    return capability in allowed
