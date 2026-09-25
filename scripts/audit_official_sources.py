"""Independent read-only comparison of the running site with freshly fetched TED XML.

Run from repository root: python scripts/audit_official_sources.py
Does not import the application parser, identity rules, or calculation functions.
Only official TED downloads and the loopback application are accessed.
"""

import csv
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser
from pathlib import Path

from defusedxml.ElementTree import fromstring

ROOT = Path(__file__).resolve().parents[1]
checks = 0
failures = []


def check(label, actual, expected):
    global checks
    checks += 1
    if actual != expected:
        failures.append({"check": label, "actual": str(actual), "expected": str(expected)})


def get(url):
    if url.startswith("https://ted.europa.eu/"):
        time.sleep(3)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read(2_000_001)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(60, int(exc.headers.get("Retry-After", "30"))))
    raise RuntimeError("Download failed")


def api(path):
    return json.loads(get("http://localhost:3000/api/v1/" + path))


def txt(node, path):
    element = node.find(path)
    return " ".join(" ".join(element.itertext()).split()) or None if element is not None else None


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def main():
    manifest = json.loads((ROOT / "data/cohort/manifest.json").read_text())
    listed = api("contracts?page_size=100")
    rows = listed["items"]
    check("all contracts fit audited page", len(rows), listed["total"])
    parties = {
        kind: {p["id"]: p for p in api(kind)["items"]} for kind in ("organizations", "suppliers")
    }
    procs = [api("procurements/" + p["id"]) for p in api("procurements?page_size=100")["items"]]
    sources = []
    expected_rows = []
    outcomes = 0
    for notice in manifest["notices"]:
        ident = notice["id"]
        assert re.fullmatch(r"\d+-\d{4}", ident)
        url = f"https://ted.europa.eu/en/notice/{ident}/xml"
        raw = get(url)
        digest = hashlib.sha256(raw).hexdigest()
        check(ident + " original checksum", digest, notice["sha256"])
        root = fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        for node in root.iter():
            node.tag = node.tag.split("}")[-1]
        form = root.find("FORM_SECTION/F03_2014[@CATEGORY='ORIGINAL'][@LG='BG']")
        assert form is not None
        publication = datetime.strptime(txt(root, ".//DATE_PUB"), "%Y%m%d").date().isoformat()
        proc = next(p for p in procs if any(n["id"] == ident for n in p["notices"]))
        check(ident + " procurement title", proc["title"], txt(form, "OBJECT_CONTRACT/TITLE"))
        check(
            ident + " reference",
            proc["reference"],
            txt(form, "PROCEDURE/NOTICE_NUMBER_OJ")
            or txt(form, "OBJECT_CONTRACT/REFERENCE_NUMBER"),
        )
        procedure = next(e.tag[3:] for e in form.find("PROCEDURE") if e.tag.startswith("PT_"))
        check(ident + " procedure", proc["procedure"], procedure)
        address = form.find("CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY")
        authority = parties["organizations"][proc["authority_id"]]
        for key, tag in (
            ("name", "OFFICIALNAME"),
            ("town", "TOWN"),
            ("official_identifier", "NATIONALID"),
        ):
            check(ident + " authority " + key, authority[key], txt(address, tag))
        check(ident + " authority country", address.find("COUNTRY").get("VALUE"), "BG")
        awards = form.findall("AWARD_CONTRACT")
        outcomes += len(awards)
        expected_outcomes = []
        notice_contracts = []
        for award in awards:
            granted = award.find("AWARDED_CONTRACT")
            reason = (
                None
                if granted is not None
                else ", ".join(e.tag for e in award.findall("NO_AWARDED_CONTRACT/*"))
                or "No award reported"
            )
            expected_outcomes.append(
                (txt(award, "LOT_NO"), "awarded" if granted is not None else "not_awarded", reason)
            )
            if granted is None:
                continue
            number = txt(award, "CONTRACT_NO")
            matches = [
                r
                for r in rows
                if r["source_number"] == number and r["source_url"].endswith("/" + ident)
            ]
            check(ident + " unique contract " + number, len(matches), 1)
            if len(matches) != 1:
                continue
            row = matches[0]
            val = granted.find("VALUES/VAL_TOTAL")
            expected = {
                "title": txt(award, "TITLE") or txt(form, "OBJECT_CONTRACT/TITLE"),
                "lot": txt(award, "LOT_NO"),
                "date": txt(granted, "DATE_CONCLUSION_CONTRACT"),
                "value": Decimal(val.text) if val is not None else None,
                "currency": val.get("CURRENCY") if val is not None else None,
                "bidders": int(txt(granted, "TENDERS/NB_TENDERS_RECEIVED")),
                "cpv": form.find("OBJECT_CONTRACT/CPV_MAIN/CPV_CODE").get("CODE"),
                "procedure": procedure,
                "authority": authority["name"],
                "location": authority["town"],
                "source_url": f"https://ted.europa.eu/bg/notice/-/detail/{ident}",
                "original_value": txt(granted, "VALUES/VAL_TOTAL"),
            }
            for field, value in expected.items():
                actual = (
                    Decimal(row[field])
                    if field == "value" and row[field] is not None
                    else row[field]
                )
                check(f"{ident}/{number} {field}", actual, value)
            expected_suppliers = []
            for supplier in granted.findall("CONTRACTORS/CONTRACTOR/ADDRESS_CONTRACTOR"):
                expected_suppliers.append(
                    (
                        txt(supplier, "OFFICIALNAME"),
                        txt(supplier, "NATIONALID"),
                        txt(supplier, "TOWN"),
                    )
                )
            actual_suppliers = [
                tuple(
                    parties["suppliers"][s["id"]][k]
                    for k in ("name", "official_identifier", "town")
                )
                for s in row["suppliers"]
            ]
            check(
                f"{ident}/{number} suppliers", sorted(actual_suppliers), sorted(expected_suppliers)
            )
            detail = api("contracts/" + row["id"])
            for field in row:
                check(f"{ident}/{number} detail {field}", detail[field], row[field])
            provenance = next(n for n in detail["provenance"] if n["notice_id"] == ident)
            check(f"{ident}/{number} provenance checksum", provenance["sha256"], digest)
            check(f"{ident}/{number} publication date", provenance["publication_date"], publication)
            check(
                f"{ident}/{number} single bid",
                detail["single_bid"]["observed"],
                expected["bidders"] == 1,
            )
            check(
                f"{ident}/{number} insufficient comparison cohort",
                detail["value_indicator"]["status"],
                "insufficient_data",
            )
            expected_rows.append({**row, **expected})
            notice_contracts.append(
                {
                    "number": number,
                    "value": str(expected["value"]),
                    "currency": expected["currency"],
                }
            )
        check(
            ident + " outcomes",
            sorted(expected_outcomes, key=str),
            sorted([(a["lot"], a["status"], a["reason"]) for a in proc["awards"]], key=str),
        )
        html_url = f"https://ted.europa.eu/en/notice/{ident}/html"
        rendered = Text()
        rendered.feed(get(html_url).decode("utf-8"))
        html_text = " ".join(" ".join(rendered.parts).split())
        if notice_contracts:
            check(ident + " official rendered VAT label", "excluding VAT" in html_text, True)
        sources.append(
            {
                "notice": ident,
                "xml_url": url,
                "rendered_url": html_url,
                "sha256": digest,
                "publication_date": publication,
                "outcomes": len(awards),
                "contracts": notice_contracts,
            }
        )
        print("Checked official TED", ident, flush=True)

    def verify_stats(label, actual, subset):
        sums = defaultdict(Decimal)
        for r in subset:
            if r["value"] is not None:
                sums[r["currency"]] += Decimal(r["value"])
        check(label + " count", actual["contracts"], len(subset))
        check(
            label + " known values",
            actual["known_values"],
            sum(r["value"] is not None for r in subset),
        )
        check(
            label + " totals",
            {c: Decimal(v) for c, v in actual["awarded_value"].items()},
            dict(sums),
        )
        check(
            label + " authority count",
            actual["organizations"],
            len({r["authority_id"] for r in subset}),
        )
        check(
            label + " supplier count",
            actual["suppliers"],
            len({s["id"] for r in subset for s in r["suppliers"]}),
        )
        for item in actual.get("months", []):
            verify_stats(
                label + " month " + item["period"],
                item,
                [r for r in subset if r["date"][:7] == item["period"]],
            )
        for item in actual.get("procedures", []):
            verify_stats(
                label + " procedure " + item["procedure"],
                item,
                [r for r in subset if r["procedure"] == item["procedure"]],
            )

    def verify_shares(label, actual, subset):
        eligible = [r for r in subset if len(r["suppliers"]) == 1 and r["value"] is not None]
        denominators = defaultdict(Decimal)
        shares = defaultdict(lambda: defaultdict(Decimal))
        for r in eligible:
            denominators[r["currency"]] += r["value"]
            shares[r["suppliers"][0]["id"]][r["currency"]] += r["value"]
        check(label + " share sample", actual["sample_size"], len(eligible))
        check(
            label + " share exclusions", actual["excluded_contracts"], len(subset) - len(eligible)
        )
        check(
            label + " share denominator",
            {k: Decimal(v) for k, v in actual["denominator"].items()},
            dict(denominators),
        )
        check(label + " share supplier set", {s["id"] for s in actual["suppliers"]}, set(shares))
        for supplier in actual["suppliers"]:
            expected = {
                c: str((v / denominators[c] * 100).quantize(Decimal("0.01")))
                if denominators[c]
                else None
                for c, v in shares[supplier["id"]].items()
            }
            check(label + " share " + supplier["id"], supplier["share_percent"], expected)

    stats = api("statistics/spending")
    verify_stats("global", stats, expected_rows)
    verify_shares("global", api("statistics/suppliers"), expected_rows)
    for kind in parties:
        for ident in parties[kind]:
            p = api(kind + "/" + ident)
            subset = (
                [r for r in expected_rows if r["authority_id"] == ident]
                if kind == "organizations"
                else [r for r in expected_rows if any(s["id"] == ident for s in r["suppliers"])]
            )
            verify_stats(kind + "/" + ident, p["statistics"], subset)
            verify_shares(kind + "/" + ident, p["concentration"], subset)
            check(
                kind + "/" + ident + " contracts",
                sorted(r["id"] for r in p["contracts"]),
                sorted(r["id"] for r in subset),
            )
    status = api("status")
    check("notice count", status["notices"], len(sources))
    check(
        "publication start", status["publication_from"], min(s["publication_date"] for s in sources)
    )
    check("publication end", status["publication_to"], max(s["publication_date"] for s in sources))
    exported = list(
        csv.DictReader(io.StringIO(get("http://localhost:3000/api/v1/export").decode("utf-8-sig")))
    )
    check("export count", len(exported), len(expected_rows))
    by_id = {r["id"]: r for r in expected_rows}
    for record in exported:
        for field in ("value", "currency", "date", "source_url"):
            check(
                "export " + record["id"] + " " + field,
                Decimal(record[field]) if field == "value" else record[field],
                by_id[record["id"]][field],
            )
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "All currently indexed records; official TED publication accuracy, not real-world delivery or payments",
        "checks": checks,
        "failures": failures,
        "notices": len(sources),
        "award_outcomes": outcomes,
        "contracts": len(expected_rows),
        "original_totals": stats["awarded_value"],
        "derived_eur_total": str(
            (
                sum(r["value"] for r in expected_rows if r["currency"] == "BGN")
                / Decimal("1.95583")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        "sources": sources,
        "limitations": [
            "Historical purposive sample, not national or current coverage",
            "No later amendments or payment records checked",
            "TED is an official EU publication service; entity registration not separately checked in Bulgarian registers",
            "Published notices may themselves contain errors",
            "Statistical observations are project calculations, not governmental findings",
        ],
    }
    (ROOT / "docs/official-source-audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "checks",
                    "failures",
                    "notices",
                    "award_outcomes",
                    "contracts",
                    "original_totals",
                    "derived_eur_total",
                )
            },
            ensure_ascii=True,
        )
    )
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
