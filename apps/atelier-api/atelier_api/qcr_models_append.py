# QCR Guild Service models — appended to models.py via import
# This file is imported by qcr_service_router.py and billing.py
# The classes are also registered by appending to models.py directly.

from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def _uuid() -> str:
    return str(uuid4())


class Department(Base):
    __tablename__ = "departments"

    id:               Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    name:             Mapped[str]      = mapped_column(String(40), nullable=False, unique=True)
    responsibilities: Mapped[str]      = mapped_column(Text,       nullable=False, default="[]")
    notes:            Mapped[str|None] = mapped_column(Text,       nullable=True)


class QCRContract(Base):
    __tablename__ = "qcr_contracts"

    id:                       Mapped[str]           = mapped_column(String(36),  primary_key=True, default=_uuid)
    dispatcher_id:            Mapped[str]           = mapped_column(String(100), nullable=False)
    client_id:                Mapped[str]           = mapped_column(String(100), nullable=False)
    tier:                     Mapped[str]           = mapped_column(String(20),  nullable=False)
    status:                   Mapped[str]           = mapped_column(String(20),  nullable=False, default="active")
    signed_at:                Mapped[datetime]      = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)
    revoked_at:               Mapped[datetime|None] = mapped_column(DateTime,    nullable=True)
    revocation_reason:        Mapped[str|None]      = mapped_column(Text,        nullable=True)
    non_erasure_acknowledged: Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=False)
    roko_last_checked:        Mapped[datetime|None] = mapped_column(DateTime,    nullable=True)
    roko_status:              Mapped[str|None]      = mapped_column(String(20),  nullable=True)
    notes:                    Mapped[str|None]      = mapped_column(Text,        nullable=True)

    implementations: Mapped[list["QCRImplementation"]] = relationship(back_populates="contract")


class QCRImplementation(Base):
    __tablename__ = "qcr_implementations"

    id:           Mapped[str]      = mapped_column(String(36),  primary_key=True, default=_uuid)
    contract_id:  Mapped[str]      = mapped_column(String(36),  ForeignKey("qcr_contracts.id"), nullable=False)
    domain:       Mapped[str]      = mapped_column(String(253), nullable=False)
    api_key:      Mapped[str]      = mapped_column(String(64),  nullable=False, unique=True)
    tier:         Mapped[str]      = mapped_column(String(20),  nullable=False)
    rate_cents:   Mapped[int]      = mapped_column(Integer,     nullable=False, default=3500)
    active:       Mapped[bool]     = mapped_column(Boolean,     nullable=False, default=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)
    notes:        Mapped[str|None] = mapped_column(Text,        nullable=True)

    contract: Mapped["QCRContract"] = relationship(back_populates="implementations")


class CostRecord(Base):
    __tablename__ = "cost_records"

    id:                  Mapped[str]      = mapped_column(String(36), primary_key=True, default=_uuid)
    period:              Mapped[str]      = mapped_column(String(7),  nullable=False)
    energy_cents:        Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    infra_cents:         Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    sulphur_wages_cents: Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    mercury_wages_cents: Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    salt_wages_cents:    Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    qqees_credit_cents:  Mapped[int]      = mapped_column(Integer,    nullable=False, default=0)
    notes:               Mapped[str|None] = mapped_column(Text,       nullable=True)

    @property
    def total_cents(self) -> int:
        return (self.energy_cents + self.infra_cents
                + self.sulphur_wages_cents + self.mercury_wages_cents
                + max(0, self.salt_wages_cents - self.qqees_credit_cents))


class RevenueShare(Base):
    __tablename__ = "revenue_shares"

    id:                      Mapped[str]           = mapped_column(String(36), primary_key=True, default=_uuid)
    period:                  Mapped[str]           = mapped_column(String(7),  nullable=False)
    implementation_id:       Mapped[str]           = mapped_column(String(36), ForeignKey("qcr_implementations.id"), nullable=False)
    revenue_cents:           Mapped[int]           = mapped_column(Integer,    nullable=False)
    total_cost_cents:        Mapped[int]           = mapped_column(Integer,    nullable=False)
    profit_cents:            Mapped[int]           = mapped_column(Integer,    nullable=False)
    dispatcher_share_cents:  Mapped[int]           = mapped_column(Integer,    nullable=False)
    practitioner_pool_cents: Mapped[int]           = mapped_column(Integer,    nullable=False)
    practitioner_pool_pct:   Mapped[float]         = mapped_column(Float,      nullable=False)
    guild_share_cents:       Mapped[int]           = mapped_column(Integer,    nullable=False)
    settled:                 Mapped[bool]          = mapped_column(Boolean,    nullable=False, default=False)
    settled_at:              Mapped[datetime|None] = mapped_column(DateTime,   nullable=True)


class QuackOffset(Base):
    __tablename__ = "quack_offsets"

    id:                   Mapped[str]      = mapped_column(String(36),  primary_key=True, default=_uuid)
    practitioner_id:      Mapped[str]      = mapped_column(String(100), nullable=False, unique=True)
    quack_count:          Mapped[int]      = mapped_column(Integer,     nullable=False, default=0)
    tongues_worked:       Mapped[int]      = mapped_column(Integer,     nullable=False, default=0)
    rank_title:           Mapped[str]      = mapped_column(String(40),  nullable=False, default="Wunashako")
    baseline_h:           Mapped[float]    = mapped_column(Float,       nullable=False, default=0.0)
    current_h:            Mapped[float]    = mapped_column(Float,       nullable=False, default=0.0)
    base_value_cents:     Mapped[int]      = mapped_column(Integer,     nullable=False, default=100)
    offset_balance_cents: Mapped[int]      = mapped_column(Integer,     nullable=False, default=0)
    last_updated:         Mapped[datetime] = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)

    @property
    def current_offset_per_quack(self) -> float:
        if self.baseline_h <= 0:
            return float(self.base_value_cents)
        return self.base_value_cents * (self.current_h / self.baseline_h)


class QCRPayment(Base):
    __tablename__ = "qcr_payments"

    id:                 Mapped[str]           = mapped_column(String(36),  primary_key=True, default=_uuid)
    implementation_id:  Mapped[str]           = mapped_column(String(36),  ForeignKey("qcr_implementations.id"), nullable=False)
    period:             Mapped[str]           = mapped_column(String(7),   nullable=False)
    amount_cents:       Mapped[int]           = mapped_column(Integer,     nullable=False)
    method:             Mapped[str]           = mapped_column(String(20),  nullable=False, default="card")
    stripe_payment_id:  Mapped[str|None]      = mapped_column(String(200), nullable=True)
    quack_offset_cents: Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)
    status:             Mapped[str]           = mapped_column(String(20),  nullable=False, default="pending")
    paid_at:            Mapped[datetime|None] = mapped_column(DateTime,    nullable=True)
    invoice_url:        Mapped[str|None]      = mapped_column(String(500), nullable=True)


class EntropySource(Base):
    __tablename__ = "entropy_sources"

    id:                       Mapped[str]           = mapped_column(String(36),  primary_key=True, default=_uuid)
    name:                     Mapped[str]           = mapped_column(String(200), nullable=False)
    source_type:              Mapped[str]           = mapped_column(String(20),  nullable=False)
    department:               Mapped[str]           = mapped_column(String(20),  nullable=False)
    description:              Mapped[str|None]      = mapped_column(Text,        nullable=True)
    registered_by:            Mapped[str]           = mapped_column(String(100), nullable=False)
    registered_at:            Mapped[datetime]      = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)
    active:                   Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)
    last_noise_at:            Mapped[datetime|None] = mapped_column(DateTime,    nullable=True)
    entropy_bits_contributed: Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)

    contributions: Mapped[list["EntropyContribution"]] = relationship(back_populates="source")


class EntropyContribution(Base):
    __tablename__ = "entropy_contributions"

    id:              Mapped[str]      = mapped_column(String(36),  primary_key=True, default=_uuid)
    source_id:       Mapped[str]      = mapped_column(String(36),  ForeignKey("entropy_sources.id"), nullable=False)
    contributed_at:  Mapped[datetime] = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)
    raw_bytes:       Mapped[int]      = mapped_column(Integer,     nullable=False)
    pool_h_after:    Mapped[float]    = mapped_column(Float,       nullable=False)
    source_type:     Mapped[str]      = mapped_column(String(20),  nullable=False)

    source: Mapped["EntropySource"] = relationship(back_populates="contributions")


class EntropyCredit(Base):
    """Credits purchased by external parties to draw from the QQEES pool."""
    __tablename__ = "entropy_credits"

    id:               Mapped[str]           = mapped_column(String(36),  primary_key=True, default=_uuid)
    holder_id:        Mapped[str]           = mapped_column(String(100), nullable=False, index=True)
    bytes_remaining:  Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)
    bytes_purchased:  Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)
    purchased_at:     Mapped[datetime]      = mapped_column(DateTime,    nullable=False, default=datetime.utcnow)
    expires_at:       Mapped[datetime|None] = mapped_column(DateTime,    nullable=True)
    stripe_session:   Mapped[str|None]      = mapped_column(String(200), nullable=True)
    api_key:          Mapped[str]           = mapped_column(String(64),  nullable=False, unique=True)
