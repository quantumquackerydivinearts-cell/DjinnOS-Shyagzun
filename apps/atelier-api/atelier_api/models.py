from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid4())


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_artisan_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    artisan_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="member")
    granted_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class Realm(Base):
    __tablename__ = "realms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    realm_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scene_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class WorldRegion(Base):
    __tablename__ = "world_regions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    realm_id: Mapped[str] = mapped_column(String(80), nullable=False)
    region_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    cache_policy: Mapped[str] = mapped_column(String(40), nullable=False, default="cache")
    loaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class ArtisanAccount(Base):
    __tablename__ = "artisan_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    artisan_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    workshop_id: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    profile_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    artisan_code_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    artisan_access_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CRMContact(Base):
    __tablename__ = "crm_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    contact_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("crm_contacts.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="scheduled")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()
    contact: Mapped[CRMContact | None] = relationship()


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LearningModule(Base):
    __tablename__ = "learning_modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="new")
    source: Mapped[str] = mapped_column(String(60), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    # Public auth fields — null until client self-registers
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    email_verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)

    workspace: Mapped[Workspace] = relationship()


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id"), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()
    lead: Mapped[Lead | None] = relationship()
    client: Mapped[Client | None] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    quote_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("quotes.id"), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()
    quote: Mapped[Quote | None] = relationship()
    client: Mapped[Client | None] = relationship()


class ClientConversation(Base):
    __tablename__ = "client_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("clients.id"), nullable=False)
    order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orders.id"), nullable=True)
    quote_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("quotes.id"), nullable=True)
    guild_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    participant_artisan_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    min_rank: Mapped[str] = mapped_column(String(40), nullable=False, default="apprentice")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()
    client: Mapped[Client] = relationship()


class ClientMessageEnvelope(Base):
    __tablename__ = "client_message_envelopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("client_conversations.id"), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # client | artisan | steward
    ciphertext_b64: Mapped[str] = mapped_column(Text, nullable=False)
    nonce_b64: Mapped[str] = mapped_column(String(60), nullable=False)
    mac_hex: Mapped[str] = mapped_column(String(64), nullable=False)
    plaintext_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[ClientConversation] = relationship()


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    party_name: Mapped[str] = mapped_column(String(200), nullable=False)
    party_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    party_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    artisan_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(60), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    section_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    supplier_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String(36), ForeignKey("lessons.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="consumed")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()
    lesson: Mapped[Lesson] = relationship()


class CharacterDictionaryEntry(Base):
    __tablename__ = "character_dictionary_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    character_id: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases_csv: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_csv: Mapped[str] = mapped_column(Text, nullable=False, default="")
    faction: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ShopItem(Base):
    __tablename__ = "shop_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    artisan_id: Mapped[str] = mapped_column(String(100), nullable=False)
    artisan_profile_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    artisan_profile_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    section_id: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Artisan marketplace fields (added migration 0024)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    item_type: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="usd")
    stripe_product_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inventory_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Legacy / steward-managed fields
    price_label: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    link_url: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    steward_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class NamedQuest(Base):
    __tablename__ = "named_quests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    quest_id: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="inactive")
    current_step: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    requirements_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    rewards_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    entry_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LayerNode(Base):
    __tablename__ = "layer_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    layer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    node_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # Multiverse stack fields — NULL for cross-game / Sulphera-level nodes
    game_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prior_subset_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LayerEdge(Base):
    __tablename__ = "layer_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    from_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("layer_nodes.id"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("layer_nodes.id"), nullable=False)
    edge_kind: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class LayerEvent(Base):
    __tablename__ = "layer_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("layer_nodes.id"), nullable=True)
    edge_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("layer_edges.id"), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class FunctionStoreEntry(Base):
    __tablename__ = "function_store_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    function_id: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    signature: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    function_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PlayerState(Base):
    __tablename__ = "player_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    levels_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    perks_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    vitriol_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    inventory_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    market_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    clock_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class RuntimePlanRun(Base):
    __tablename__ = "runtime_plan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(160), nullable=False)
    plan_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    plan_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class AssetManifest(Base):
    __tablename__ = "asset_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id"), nullable=False)
    realm_id: Mapped[str] = mapped_column(String(80), nullable=False, default="lapidus")
    manifest_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    storage_state: Mapped[str] = mapped_column(String(40), nullable=False, default="local")
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/octet-stream")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    workspace: Mapped[Workspace] = relationship()


class KernelField(Base):
    __tablename__ = "kernel_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    field_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    owner_artisan_id: Mapped[str] = mapped_column(String(100), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    issued_by: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="artisan")
    workshop_id: Mapped[str] = mapped_column(String(100), nullable=False)
    max_uses: Mapped[int] = mapped_column(nullable=False, default=1)
    uses_count: Mapped[int] = mapped_column(nullable=False, default=0)
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class GuildMessageEnvelopeRecord(Base):
    __tablename__ = "guild_message_envelopes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    conversation_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    conversation_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="guild_channel")
    guild_id: Mapped[str] = mapped_column(String(160), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(160), nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sender_id: Mapped[str] = mapped_column(String(160), nullable=False)
    wand_id: Mapped[str] = mapped_column(String(160), nullable=False)
    envelope_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class GuildConversationRecord(Base):
    __tablename__ = "guild_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    conversation_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="guild_channel")
    guild_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    channel_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    participant_member_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    participant_guild_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    distribution_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    security_session_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class WandDamageAttestationRecord(Base):
    __tablename__ = "wand_damage_attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    record_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    wand_id: Mapped[str] = mapped_column(String(160), nullable=False)
    notifier_id: Mapped[str] = mapped_column(String(160), nullable=False)
    damage_state: Mapped[str] = mapped_column(String(80), nullable=False)
    event_tag: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    workshop_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    media_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    validated_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class WandKeyEpochRecord(Base):
    __tablename__ = "wand_key_epochs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    epoch_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    wand_id: Mapped[str] = mapped_column(String(160), nullable=False)
    attestation_record_id: Mapped[str] = mapped_column(String(80), nullable=False)
    notifier_id: Mapped[str] = mapped_column(String(160), nullable=False)
    previous_epoch_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    damage_state: Mapped[str] = mapped_column(String(80), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entropy_mix_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class WandRegistryRecord(Base):
    __tablename__ = "wand_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    wand_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    maker_id: Mapped[str] = mapped_column(String(160), nullable=False)
    maker_date: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    atelier_origin: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    material_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    dimensions_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    structural_fingerprint: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    craft_record_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    ownership_chain_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class GuildRegistryRecord(Base):
    __tablename__ = "guild_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    guild_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    distribution_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    owner_artisan_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    owner_profile_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    owner_profile_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    member_profiles_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    charter_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DistributionRegistryRecord(Base):
    __tablename__ = "distribution_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    distribution_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    transport_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="https")
    public_key_ref: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    guild_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class DistributionHandshakeRecord(Base):
    __tablename__ = "distribution_handshakes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    handshake_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    distribution_id: Mapped[str] = mapped_column(String(200), nullable=False)
    local_distribution_id: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    remote_public_key_ref: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    handshake_mode: Mapped[str] = mapped_column(String(80), nullable=False, default="mutual_hmac")
    shared_secret_b64: Mapped[str] = mapped_column(Text, nullable=False, default="")
    shared_secret_digest: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class GuildArtisanProfile(Base):
    __tablename__ = "guild_artisan_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    artisan_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    portfolio_url: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    avatar_url: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    divisions: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    trades: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    guild_rank: Mapped[str] = mapped_column(String(40), nullable=False, default="artisan")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_region: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_trades: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_portfolio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    steward_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Stripe Connect account ID — populated when artisan completes Connect onboarding
    stripe_account_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
