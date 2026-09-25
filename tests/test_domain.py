from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from defusedxml.common import DTDForbidden

from backend.indicators import value_indicator
from backend.main import Filters, safe_csv
from backend.service import concentration, totals
from pipeline.extract import validate_url
from pipeline.transform import amount, identity, transform


@pytest.mark.parametrize(
    "raw", ["NaN", "Infinity", "-1", "1,000", "1e5", "1.1234567", "1000000000000000000"]
)
def test_amount_rejects_ambiguous_or_unrepresentable(raw):
    with pytest.raises(ValueError):
        amount(raw)


def test_exact_amounts_and_identifiers():
    assert amount("0.10") + amount("0.20") == Decimal("0.30")
    assert amount(None) is None
    assert identity("BG", "001") != identity("BG", "1")
    assert identity("BG", "001") != identity("DE", "001")


def test_real_fixture_reconciliation():
    notices = [transform(p.read_bytes()) for p in Path("tests/fixtures").glob("*.xml")]
    assert len(notices) == 12
    outcomes = [a for n in notices for a in n.results]
    assert len(outcomes) == 15
    assert sum(a.status == "awarded" for a in outcomes) == 11
    assert sum((a.value or Decimal(0) for a in outcomes), Decimal(0)) == Decimal("5367011.18")
    assert {a.currency for a in outcomes if a.value is not None} == {"BGN"}
    assert next(n for n in notices if n.id == "2510-2023").results[0].lot == "1"


def test_parser_rejects_entities_and_other_forms():
    with pytest.raises(DTDForbidden):
        transform(b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')
    with pytest.raises(ValueError):
        transform(b"<unknown/>")
    with pytest.raises(ValueError):
        transform(b"x" * 2_000_001)


@pytest.mark.parametrize(
    "url",
    [
        "http://ted.europa.eu/en/notice/1-2023/xml",
        "https://127.0.0.1/en/notice/1-2023/xml",
        "https://ted.europa.eu.evil.test/en/notice/1-2023/xml",
        "https://ted.europa.eu@evil.test/en/notice/1-2023/xml",
        "https://ted.europa.eu/en/notice/1-2023/xml?url=http://169.254.169.254",
        "https://ted.europa.eu:444/en/notice/1-2023/xml",
    ],
)
def test_source_allowlist(url):
    with pytest.raises(ValueError):
        validate_url(url, resolve=False)


def test_indicators_have_explicit_ineligible_states():
    assert value_indicator(None, [])["status"] == "insufficient_data"
    assert value_indicator(Decimal(1000), [Decimal(1)] * 10)["status"] == "zero_dispersion"
    assert (
        value_indicator(Decimal(1000), [Decimal(i) for i in range(10)])["status"]
        == "above_threshold"
    )
    assert (
        value_indicator(Decimal(5), [Decimal(i) for i in range(10)])["status"] == "within_threshold"
    )


def test_no_currency_mixing_or_joint_allocation():
    rows = [
        {
            "id": "1",
            "value": Decimal(10),
            "currency": "EUR",
            "authority_id": "a",
            "suppliers": [{"id": "s", "name": "S"}],
        },
        {
            "id": "2",
            "value": Decimal(20),
            "currency": "BGN",
            "authority_id": "a",
            "suppliers": [{"id": "s", "name": "S"}, {"id": "t", "name": "T"}],
        },
    ]
    assert totals(rows)["awarded_value"] == {"BGN": "20", "EUR": "10"}
    shares = concentration(rows)
    assert shares["sample_size"] == 1
    assert shares["excluded_contracts"] == 1
    assert shares["denominator"] == {"EUR": "10"}


@pytest.mark.parametrize(
    "value", ["=HYPERLINK(1)", " +SUM(1)", "-1+2", "@SUM(1)", "\tfoo", "\rfoo", "\nfoo"]
)
def test_csv_formula_safety(value):
    assert safe_csv(value).startswith("'")


def test_filters_validate_currency_and_ranges():
    with pytest.raises(ValueError):
        Filters(sort="value_desc")
    with pytest.raises(ValueError):
        Filters(from_date="2023-02-01", to_date="2023-01-01")
    with pytest.raises(ValueError):
        Filters(currency="EUR", min_value="10", max_value="1")
    assert Filters(currency="EUR", min_value="0").min_value == 0


def test_missing_supplier_country_is_not_invented():
    root = ET.parse("tests/fixtures/2291-2023.xml").getroot()
    supplier = root.find(".//{*}ADDRESS_CONTRACTOR")
    supplier.remove(supplier.find("{*}COUNTRY"))
    with pytest.raises(ValueError, match="Party country not reported"):
        transform(ET.tostring(root))
