"""Read models for the bounded cohort. Money stays Decimal until JSON serialization."""

from collections import defaultdict
from decimal import Decimal
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Contract, ContractSupplier, Notice, Organization, Procurement, Supplier


def records(db: Session) -> list[dict]:
    rows = db.execute(
        select(Contract, Procurement, Organization)
        .join(Procurement, Contract.procurement_id == Procurement.id)
        .join(Organization, Procurement.authority_id == Organization.id)
        .limit(10001)
    ).all()
    if len(rows) > 10000:
        raise HTTPException(503, "Cohort exceeds the configured 10,000-contract query limit")
    links: dict[str, list[dict]] = defaultdict(list)
    for link, supplier in db.execute(select(ContractSupplier, Supplier).join(Supplier)):
        links[link.contract_id].append({"id": supplier.id, "name": supplier.name})
    return [
        {
            "id": c.id,
            "procurement_id": p.id,
            "title": c.title,
            "source_number": c.source_number,
            "authority_id": o.id,
            "authority": o.name,
            "location": o.town,
            "procedure": p.procedure,
            "cpv": p.cpv,
            "lot": c.lot,
            "date": c.conclusion_date.isoformat() if c.conclusion_date else None,
            "value": c.value,
            "currency": c.currency,
            "vat": c.vat,
            "bidders": c.bidders,
            "suppliers": sorted(links[c.id], key=lambda s: s["id"]),
            "source_url": c.source_url,
            "original_value": c.original_value,
        }
        for c, p, o in rows
    ]


def snapshot(db: Session) -> str:
    return sha256(
        "|".join(
            f"{n.id}:{n.checksum}" for n in db.scalars(select(Notice).order_by(Notice.id))
        ).encode()
    ).hexdigest()[:20]


def totals(rows: list[dict]) -> dict:
    values: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        if row["value"] is not None:
            values[row["currency"]] += row["value"]
    return {
        "contracts": len(rows),
        "known_values": sum(r["value"] is not None for r in rows),
        "awarded_value": {k: str(v) for k, v in sorted(values.items())},
        "organizations": len({r["authority_id"] for r in rows}),
        "suppliers": len({s["id"] for r in rows for s in r["suppliers"]}),
    }


def statistics(rows: list[dict]) -> dict:
    monthly: dict[str, list[dict]] = defaultdict(list)
    procedures: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        monthly[(r["date"] or "Unknown")[:7]].append(r)
        procedures[r["procedure"]].append(r)
    return {
        **totals(rows),
        "months": [{"period": k, **totals(v)} for k, v in sorted(monthly.items())],
        "procedures": [{"procedure": k, **totals(v)} for k, v in sorted(procedures.items())],
    }


def concentration(rows: list[dict]) -> dict:
    eligible = [r for r in rows if len(r["suppliers"]) == 1 and r["value"] is not None]
    denominator = totals(eligible)["awarded_value"]
    suppliers: dict[str, list[dict]] = defaultdict(list)
    names = {}
    for r in eligible:
        s = r["suppliers"][0]
        suppliers[s["id"]].append(r)
        names[s["id"]] = s["name"]
    return {
        "name": "Supplier share of sole-supplier award value",
        "algorithm_version": "share-1.0.0",
        "formula": "sole-supplier value / eligible selected-record value in the same currency × 100",
        "time_window": "Selected indexed records",
        "sample_size": len(eligible),
        "threshold": None,
        "excluded_contracts": len(rows) - len(eligible),
        "denominator": denominator,
        "limitations": "Joint awards and missing values excluded. Small, incomplete samples are not market shares or evidence of misconduct.",
        "suppliers": [
            {
                "id": k,
                "name": names[k],
                **totals(v),
                "share_percent": {
                    currency: str(
                        (Decimal(value) / Decimal(denominator[currency]) * 100).quantize(
                            Decimal("0.01")
                        )
                    )
                    if Decimal(denominator[currency])
                    else None
                    for currency, value in totals(v)["awarded_value"].items()
                },
            }
            for k, v in sorted(suppliers.items())
        ],
    }
