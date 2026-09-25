from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    official_identifier: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str | None] = mapped_column(String(80))


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    official_identifier: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(Text)
    town: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(2))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    seen: Mapped[int] = mapped_column(default=0)
    inserted: Mapped[int] = mapped_column(default=0)
    updated: Mapped[int] = mapped_column(default=0)
    unchanged: Mapped[int] = mapped_column(default=0)
    quarantined: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


class Procurement(Base):
    __tablename__ = "procurements"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    authority_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    reference: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    procedure: Mapped[str] = mapped_column(String(80), index=True)
    cpv: Mapped[str | None] = mapped_column(String(8))


class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    procurement_id: Mapped[str] = mapped_column(ForeignKey("procurements.id"), index=True)
    publication_date: Mapped[date] = mapped_column(index=True)
    source_url: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[str] = mapped_column(ForeignKey("ingestion_runs.id"))
    transform_version: Mapped[str] = mapped_column(String(30))
    snapshot: Mapped[dict] = mapped_column(JSON)


class NoticeVersion(Base):
    __tablename__ = "notice_versions"
    __table_args__ = (UniqueConstraint("notice_id", "checksum"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[str] = mapped_column(ForeignKey("notices.id"))
    checksum: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    replaced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Award(Base):
    __tablename__ = "awards"
    __table_args__ = (UniqueConstraint("notice_id", "source_item"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    notice_id: Mapped[str] = mapped_column(ForeignKey("notices.id"), index=True)
    source_item: Mapped[str] = mapped_column(String(40))
    lot: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    contract_id: Mapped[str | None] = mapped_column(ForeignKey("contracts.id"), index=True)


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("value IS NULL OR value >= 0"),
        CheckConstraint("bidders IS NULL OR bidders >= 0"),
        CheckConstraint("(value IS NULL) = (currency IS NULL)"),
        Index("ix_contract_date_id", "conclusion_date", "id"),
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    procurement_id: Mapped[str] = mapped_column(ForeignKey("procurements.id"), index=True)
    source_number: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    lot: Mapped[str | None] = mapped_column(Text)
    conclusion_date: Mapped[date | None]
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    currency: Mapped[str | None] = mapped_column(String(3), index=True)
    original_value: Mapped[str | None] = mapped_column(Text)
    vat: Mapped[str] = mapped_column(String(30), default="excluded")
    bidders: Mapped[int | None]
    source_url: Mapped[str] = mapped_column(Text)


class ContractSupplier(Base):
    __tablename__ = "contract_suppliers"
    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True
    )
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), primary_key=True)
