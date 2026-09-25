from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import (
    Award,
    Contract,
    ContractSupplier,
    Notice,
    NoticeVersion,
    Organization,
    Procurement,
    Supplier,
)
from pipeline.transform import VERSION, Record, identity


def load(
    db: Session, record: Record, checksum: str, source_url: str, retrieved_at: datetime, run_id: str
) -> str:
    old = db.get(Notice, record.id)
    if old and old.checksum == checksum:
        return "unchanged"
    snapshot = record.model_dump(mode="json")
    if old:
        existing = db.scalar(
            select(NoticeVersion).where(
                NoticeVersion.notice_id == old.id, NoticeVersion.checksum == old.checksum
            )
        )
        if not existing:
            db.add(
                NoticeVersion(
                    notice_id=old.id,
                    checksum=old.checksum,
                    snapshot=old.snapshot,
                    replaced_at=datetime.now(UTC),
                )
            )
        # Changes to the bounded, original-notice cohort require review rather than stale aggregates.
        if old.snapshot != snapshot:
            raise ValueError(
                "Source content changed: review and migrate the cohort before replacing financial records"
            )
    db.merge(Organization(**record.authority.model_dump(), kind=record.kind))
    db.flush()
    db.merge(
        Procurement(
            id=record.procurement_id,
            authority_id=record.authority.id,
            reference=record.reference,
            title=record.title,
            procedure=record.procedure,
            cpv=record.cpv,
        )
    )
    db.flush()
    db.merge(
        Notice(
            id=record.id,
            procurement_id=record.procurement_id,
            publication_date=record.publication_date,
            source_url=source_url,
            checksum=checksum,
            retrieved_at=retrieved_at,
            run_id=run_id,
            transform_version=VERSION,
            snapshot=snapshot,
        )
    )
    db.flush()
    for result in record.results:
        contract_id = None
        if result.status == "awarded":
            assert result.number is not None
            contract_id = identity(
                "ted-contract", record.authority.id, record.procurement_id, result.number
            )
            contract = Contract(
                id=contract_id,
                procurement_id=record.procurement_id,
                source_number=result.number,
                title=result.title,
                lot=result.lot,
                conclusion_date=result.conclusion_date,
                value=result.value,
                currency=result.currency,
                original_value=result.original_value,
                bidders=result.bidders,
                vat="excluded",
                source_url=source_url,
            )
            previous = db.get(Contract, contract_id)
            if previous and (
                previous.value != contract.value or previous.currency != contract.currency
            ):
                raise ValueError("Conflicting contract value across notices; review required")
            db.merge(contract)
            for supplier in result.suppliers:
                db.merge(Supplier(**supplier.model_dump()))
            db.flush()
            db.execute(delete(ContractSupplier).where(ContractSupplier.contract_id == contract_id))
            for supplier_id in {s.id for s in result.suppliers}:
                db.add(ContractSupplier(contract_id=contract_id, supplier_id=supplier_id))
        db.add(
            Award(
                id=identity("ted-award", record.id, result.item),
                notice_id=record.id,
                source_item=result.item,
                lot=result.lot,
                status=result.status,
                reason=result.reason,
                contract_id=contract_id,
            )
        ) if not old else None
    db.flush()
    return "updated" if old else "inserted"
