import csv
import io
import json
import logging
import time
import uuid
from collections import OrderedDict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.db import session
from backend.indicators import value_indicator
from backend.models import Award, IngestionRun, Notice, Organization, Procurement, Supplier
from backend.service import concentration, records, snapshot, statistics

app = FastAPI(
    title="BG Transparency Explorer",
    version="1.0.0",
    description="Read-only API. Award values, not payments. Limited historical TED sample.",
)
DB = Annotated[Session, Depends(session)]
logger = logging.getLogger("bg.api")
buckets: OrderedDict[str, tuple[float, int]] = OrderedDict()


def encode(value):
    return jsonable_encoder(value, custom_encoder={Decimal: str})


@app.middleware("http")
async def guards(request: Request, call_next):
    started = time.monotonic()
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    key = request.client.host if request.client else "unknown"
    start, count = buckets.get(key, (started, 0))
    if started - start > 60:
        start, count = started, 0
    buckets[key] = (start, count + 1)
    buckets.move_to_end(key)
    if len(buckets) > 10000:
        buckets.popitem(last=False)
    if count >= 120:
        response = JSONResponse(
            {"error": "rate_limited", "request_id": request_id}, 429, headers={"Retry-After": "60"}
        )
    elif request.method not in ("GET", "HEAD", "OPTIONS"):
        response = JSONResponse({"error": "Public API is read-only", "request_id": request_id}, 405)
    elif len(request.url.query) > 4096 or request.headers.get("content-length", "0") != "0":
        response = JSONResponse({"error": "request_too_large", "request_id": request_id}, 413)
    else:
        response = await call_next(request)
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        }
    )
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(
        {"error": exc.detail, "request_id": request.state.request_id}, exc.status_code
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "error": "Invalid query parameters",
            "fields": [str(e["loc"][-1]) for e in exc.errors()],
            "request_id": request.state.request_id,
        },
        422,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(
        {"error": "Data temporarily unavailable", "request_id": request.state.request_id}, 503
    )


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str = Field(default="", max_length=200)
    authority: str | None = Field(default=None, max_length=80)
    supplier: str | None = Field(default=None, max_length=80)
    procedure: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    from_date: date | None = None
    to_date: date | None = None
    min_value: Decimal | None = Field(default=None, ge=0, max_digits=24, decimal_places=6)
    max_value: Decimal | None = Field(default=None, ge=0, max_digits=24, decimal_places=6)
    sort: Literal["date_desc", "date_asc", "value_desc", "value_asc", "title"] = "date_desc"
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=25, ge=1, le=100)
    snapshot: str | None = Field(default=None, pattern=r"^[a-f0-9]{20}$")

    @model_validator(mode="after")
    def valid_range(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("Inverted dates")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("Inverted values")
        if (
            self.min_value is not None
            or self.max_value is not None
            or self.sort.startswith("value")
        ) and not self.currency:
            raise ValueError("Value filters and sorting require a currency")
        return self


def filtered(db: Session, f: Filters):
    token = snapshot(db)
    if f.snapshot and f.snapshot != token:
        raise HTTPException(409, "Dataset changed. Restart pagination.")
    result = []
    for r in records(db):
        if (
            f.q.casefold()
            not in (
                r["title"]
                + " "
                + r["authority"]
                + " "
                + " ".join(s["name"] for s in r["suppliers"])
            ).casefold()
        ):
            continue
        if any(
            value and r[field] != value
            for field, value in [
                ("authority_id", f.authority),
                ("procedure", f.procedure),
                ("location", f.location),
                ("currency", f.currency),
            ]
        ):
            continue
        if f.supplier and f.supplier not in {s["id"] for s in r["suppliers"]}:
            continue
        if f.from_date and (not r["date"] or r["date"] < f.from_date.isoformat()):
            continue
        if f.to_date and (not r["date"] or r["date"] > f.to_date.isoformat()):
            continue
        if f.min_value is not None and (r["value"] is None or r["value"] < f.min_value):
            continue
        if f.max_value is not None and (r["value"] is None or r["value"] > f.max_value):
            continue
        result.append(r)
    field = "value" if f.sort.startswith("value") else "title" if f.sort == "title" else "date"
    known, missing = (
        [r for r in result if r[field] is not None],
        [r for r in result if r[field] is None],
    )
    known.sort(key=lambda r: (r[field], r["id"]), reverse=f.sort.endswith("desc"))
    return known + sorted(missing, key=lambda r: r["id"]), token


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: DB):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/api/v1/contracts")
@app.get("/api/v1/search")
def search(db: DB, f: Annotated[Filters, Query()]):
    rows, token = filtered(db, f)
    start = (f.page - 1) * f.page_size
    return JSONResponse(
        encode(
            {
                "items": rows[start : start + f.page_size],
                "total": len(rows),
                "page": f.page,
                "page_size": f.page_size,
                "snapshot": token,
            }
        )
    )


@app.get("/api/v1/contracts/{identifier}")
def detail(identifier: str, db: DB):
    rows = records(db)
    row = next((r for r in rows if r["id"] == identifier), None)
    if not row:
        raise HTTPException(404, "Contract not found")
    peers = [
        r["value"]
        for r in rows
        if r["id"] != row["id"]
        and r["value"] is not None
        and r["date"]
        and row["date"]
        and r["date"][:4] == row["date"][:4]
        and r["currency"] == row["currency"]
        and r["procedure"] == row["procedure"]
        and r["cpv"]
        and row["cpv"]
        and r["cpv"][:2] == row["cpv"][:2]
    ]
    notices = db.scalars(
        select(Notice)
        .join(Award, Award.notice_id == Notice.id)
        .where(Award.contract_id == identifier)
    ).all()
    return JSONResponse(
        encode(
            {
                **row,
                "value_indicator": value_indicator(row["value"], peers),
                "single_bid": {
                    "name": "Reported single bid",
                    "observed": row["bidders"] == 1 if row["bidders"] is not None else None,
                    "input": row["bidders"],
                    "formula": "reported tenders received = 1",
                    "algorithm_version": "single-bid-1.0.0",
                    "sample_size": 1,
                    "threshold": 1,
                    "limitations": "Observation about this award; not a statistical outlier or evidence of misconduct.",
                },
                "provenance": [
                    {
                        "notice_id": n.id,
                        "source_url": n.source_url,
                        "publication_date": n.publication_date,
                        "retrieved_at": n.retrieved_at,
                        "sha256": n.checksum,
                        "run_id": n.run_id,
                        "transform_version": n.transform_version,
                    }
                    for n in notices
                ],
            }
        )
    )


@app.get("/api/v1/procurements")
def procurements(db: DB, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    return {
        "items": [
            dict(id=p.id, title=p.title, authority_id=p.authority_id, procedure=p.procedure)
            for p in db.scalars(
                select(Procurement)
                .order_by(Procurement.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ]
    }


@app.get("/api/v1/procurements/{identifier}")
def procurement(identifier: str, db: DB):
    p = db.get(Procurement, identifier)
    if not p:
        raise HTTPException(404, "Procurement not found")
    notices = db.scalars(select(Notice).where(Notice.procurement_id == identifier)).all()
    awards = db.scalars(select(Award).join(Notice).where(Notice.procurement_id == identifier)).all()
    return JSONResponse(
        encode(
            {
                "id": p.id,
                "title": p.title,
                "reference": p.reference,
                "authority_id": p.authority_id,
                "procedure": p.procedure,
                "contracts": [r for r in records(db) if r["procurement_id"] == identifier],
                "awards": [
                    {
                        "id": a.id,
                        "lot": a.lot,
                        "status": a.status,
                        "reason": a.reason,
                        "contract_id": a.contract_id,
                    }
                    for a in awards
                ],
                "notices": [
                    {"id": n.id, "publication_date": n.publication_date, "source_url": n.source_url}
                    for n in notices
                ],
            }
        )
    )


@app.get("/api/v1/organizations")
def organizations(db: DB):
    return {
        "items": [
            {
                "id": x.id,
                "name": x.name,
                "town": x.town,
                "official_identifier": x.official_identifier,
            }
            for x in db.scalars(select(Organization).order_by(Organization.name).limit(1000))
        ]
    }


@app.get("/api/v1/suppliers")
def suppliers(db: DB):
    return {
        "items": [
            {
                "id": x.id,
                "name": x.name,
                "town": x.town,
                "official_identifier": x.official_identifier,
            }
            for x in db.scalars(select(Supplier).order_by(Supplier.name).limit(1000))
        ]
    }


def profile(db, model, identifier):
    entity = db.get(model, identifier)
    if not entity:
        raise HTTPException(404, "Entity not found")
    rows = (
        [r for r in records(db) if r["authority_id"] == identifier]
        if model is Organization
        else [r for r in records(db) if any(s["id"] == identifier for s in r["suppliers"])]
    )
    return JSONResponse(
        encode(
            {
                "id": entity.id,
                "name": entity.name,
                "town": entity.town,
                "official_identifier": entity.official_identifier,
                "statistics": statistics(rows),
                "concentration": concentration(rows),
                "contracts": rows,
            }
        )
    )


@app.get("/api/v1/organizations/{identifier}")
def organization(identifier: str, db: DB):
    return profile(db, Organization, identifier)


@app.get("/api/v1/suppliers/{identifier}")
def supplier(identifier: str, db: DB):
    return profile(db, Supplier, identifier)


@app.get("/api/v1/statistics/spending")
def spending(db: DB, f: Annotated[Filters, Query()]):
    rows, token = filtered(db, f)
    return {
        **statistics(rows),
        "snapshot": token,
        "meaning": "Awarded contract values excluding VAT; not actual payments",
    }


@app.get("/api/v1/statistics/suppliers")
def supplier_statistics(db: DB, f: Annotated[Filters, Query()]):
    rows, _ = filtered(db, f)
    return concentration(rows)


def safe_csv(value) -> str:
    result = str(value) if value is not None else ""
    return (
        "'" + result
        if result.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
        or result.startswith(("\t", "\r", "\n"))
        else result
    )


@app.get("/api/v1/export")
def export(db: DB, f: Annotated[Filters, Query()]):
    rows, _ = filtered(db, f)
    if len(rows) > 1000:
        raise HTTPException(422, "Export exceeds 1,000 rows; narrow the filters")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    fields = ["id", "title", "authority", "date", "value", "currency", "vat", "source_url"]
    writer.writerow(fields)
    for row in rows:
        writer.writerow([safe_csv(row[f]) for f in fields])
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="bg-award-values.csv"'},
    )


@app.get("/api/v1/status")
def status(db: DB):
    last = db.scalar(
        select(IngestionRun)
        .where(IngestionRun.status == "success")
        .order_by(IngestionRun.completed_at.desc())
        .limit(1)
    )
    runs = db.scalars(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(10)).all()
    pub = db.execute(
        select(
            func.min(Notice.publication_date),
            func.max(Notice.publication_date),
            func.count(Notice.id),
        )
    ).one()
    return {
        "source": "Tenders Electronic Daily — Publications Office of the European Union",
        "source_url": "https://ted.europa.eu/en/",
        "reuse_url": "https://ted.europa.eu/en/legal-notice",
        "coverage": "Fixed sample of 12 original Bulgarian F03 notices selected from a 1–7 January 2023 query. Not representative of national spending.",
        "notices": pub[2],
        "publication_from": pub[0],
        "publication_to": pub[1],
        "historical_sample": True,
        "last_success": last.completed_at if last else None,
        "freshness": "not_imported"
        if not last or not last.completed_at
        else "stale_check"
        if (datetime.now(UTC) - last.completed_at).total_seconds() > 172800
        else "checked",
        "runs": [
            {
                "id": r.id,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "seen": r.seen,
                "inserted": r.inserted,
                "updated": r.updated,
                "unchanged": r.unchanged,
                "quarantined": r.quarantined,
            }
            for r in runs
        ],
    }
