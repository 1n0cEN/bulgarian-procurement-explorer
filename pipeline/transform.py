"""Strict adapter for original Bulgarian TED legacy F03 notices, not eForms."""

import hashlib
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring
from pydantic import BaseModel, ConfigDict, Field

VERSION = "ted-f03-1.0.0"


def identity(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def text(node: Element, path: str) -> str | None:
    found = node.find(path)
    return " ".join(" ".join(found.itertext()).split()) or None if found is not None else None


def attr(node: Element, path: str, name: str) -> str | None:
    found = node.find(path)
    return found.get(name) if found is not None else None


def amount(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    if not re.fullmatch(r"\d+(\.\d{1,6})?", raw):
        raise ValueError("Invalid exact decimal amount")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if value >= Decimal("1e18"):
        raise ValueError("Amount exceeds storage precision")
    return value


class Party(BaseModel):
    id: str
    official_identifier: str | None
    name: str = Field(min_length=1, max_length=2000)
    town: str | None
    country: str = Field(pattern=r"^[A-Z]{2}$")


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str
    lot: str | None
    status: str
    reason: str | None = None
    number: str | None = None
    title: str
    conclusion_date: date | None = None
    value: Decimal | None = None
    original_value: str | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    bidders: int | None = Field(default=None, ge=0)
    suppliers: list[Party] = []


class Record(BaseModel):
    id: str
    procurement_id: str
    reference: str | None
    publication_date: date
    title: str
    procedure: str
    cpv: str | None
    authority: Party
    kind: str | None
    results: list[Result]


def party(node: Element, fallback: str) -> Party:
    identifier = text(node, "NATIONALID")
    country = attr(node, "COUNTRY", "VALUE") or "BG"
    return Party(
        id=identity("ted", country, identifier or fallback),
        official_identifier=identifier,
        name=text(node, "OFFICIALNAME") or "Name not reported",
        town=text(node, "TOWN"),
        country=country,
    )


def transform(raw: bytes) -> Record:
    if len(raw) > 2_000_000:
        raise ValueError("XML exceeds 2 MB limit")
    root = fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]
    forms = root.findall("FORM_SECTION/F03_2014[@CATEGORY='ORIGINAL'][@LG='BG']")
    if len(forms) != 1 or not root.get("VERSION", "").startswith("R2.0.9"):
        raise ValueError("Unsupported source schema: expected one original Bulgarian R2.0.9 F03")
    form = forms[0]
    raw_id = root.get("DOC_ID", "")
    if not re.fullmatch(r"\d{1,6}-\d{4}", raw_id):
        raise ValueError("Invalid publication identifier")
    ident = str(int(raw_id.split("-")[0])) + "-" + raw_id.split("-")[1]
    address = form.find("CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY")
    if address is None or attr(address, "COUNTRY", "VALUE") != "BG":
        raise ValueError("Missing Bulgarian authority")
    authority = party(address, ident + ":authority")
    reference = text(form, "PROCEDURE/NOTICE_NUMBER_OJ") or text(
        form, "OBJECT_CONTRACT/REFERENCE_NUMBER"
    )
    procurement_id = identity("ted", authority.id, reference or ident)
    title = text(form, "OBJECT_CONTRACT/TITLE") or "Title not reported"
    procedure = next(
        (e.tag.removeprefix("PT_") for e in form.findall("PROCEDURE/*") if e.tag.startswith("PT_")),
        "NOT_REPORTED",
    )
    results = []
    for award in form.findall("AWARD_CONTRACT"):
        item = award.get("ITEM")
        if not item:
            raise ValueError("Missing award ITEM")
        result = Result(
            item=item,
            lot=text(award, "LOT_NO"),
            title=text(award, "TITLE") or title,
            status="not_awarded",
            reason=None,
        )
        granted = award.find("AWARDED_CONTRACT")
        if granted is None:
            result.reason = (
                ", ".join(e.tag for e in award.findall("NO_AWARDED_CONTRACT/*"))
                or "No award reported"
            )
        else:
            result.status = "awarded"
            result.number = text(award, "CONTRACT_NO")
            if not result.number:
                raise ValueError("Award without contract number cannot be safely deduplicated")
            raw_date = text(granted, "DATE_CONCLUSION_CONTRACT")
            result.conclusion_date = date.fromisoformat(raw_date) if raw_date else None
            result.original_value = text(granted, "VALUES/VAL_TOTAL")
            result.value = amount(result.original_value)
            result.currency = (
                attr(granted, "VALUES/VAL_TOTAL", "CURRENCY") if result.value is not None else None
            )
            if result.value is not None and not result.currency:
                raise ValueError("Amount without currency")
            bids = text(granted, "TENDERS/NB_TENDERS_RECEIVED")
            result.bidders = int(bids) if bids is not None else None
            result.suppliers = [
                party(p, f"{ident}:{item}:supplier:{i}")
                for i, p in enumerate(granted.findall("CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR"))
            ]
        results.append(Result.model_validate(result.model_dump()))
    if len({r.item for r in results}) != len(results) or not results:
        raise ValueError("Missing or duplicate award items")
    pub = text(root, ".//DATE_PUB")
    if pub is None:
        raise ValueError("Missing publication date")
    return Record(
        id=ident,
        procurement_id=procurement_id,
        reference=reference,
        publication_date=date.fromisoformat(pub),
        title=title,
        procedure=procedure,
        cpv=attr(form, "OBJECT_CONTRACT/CPV_MAIN/CPV_CODE", "CODE"),
        authority=authority,
        kind=attr(form, "CONTRACTING_BODY/CA_TYPE", "VALUE"),
        results=results,
    )
