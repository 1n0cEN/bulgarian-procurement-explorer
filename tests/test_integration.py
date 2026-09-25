import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.main import app, buckets
from backend.models import Base, Contract, IngestionRun, Notice
from pipeline.run_pipeline import run

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated real PostgreSQL test database")
    if not url.endswith("/bg_test"):
        raise RuntimeError("Integration tests only run against a database named bg_test")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    engine.cache_clear()
    Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())
    yield
    engine().dispose()
    engine.cache_clear()
    if previous:
        os.environ["DATABASE_URL"] = previous


def test_repeated_import_and_atomic_recovery(tmp_path):
    manifest = Path("tests/fixtures/manifest.json")
    assert run(manifest)["inserted"] == 12
    assert run(manifest)["unchanged"] == 12
    with Session(engine()) as db:
        assert db.scalar(select(func.count(Contract.id))) == 11
        assert str(db.scalar(select(func.sum(Contract.value)))) == "5367011.180000"
        assert db.scalar(select(func.count(Notice.id))) == 12
    broken = json.loads(manifest.read_text())
    broken["notices"][0]["sha256"] = "0" * 64
    # All fixture files are copied to the new manifest directory.
    for p in manifest.parent.glob("*.xml"):
        (tmp_path / p.name).write_bytes(p.read_bytes())
    (tmp_path / "manifest.json").write_text(json.dumps(broken))
    with pytest.raises(RuntimeError):
        run(tmp_path / "manifest.json")
    with Session(engine()) as db:
        assert db.scalar(select(func.count(Contract.id))) == 11
        assert (
            db.scalar(select(IngestionRun.status).order_by(IngestionRun.started_at.desc()).limit(1))
            == "failed"
        )
    assert run(manifest)["unchanged"] == 12


def test_api_filters_pagination_details_and_profiles():
    buckets.clear()
    client = TestClient(app)
    r = client.get("/api/v1/contracts?page_size=3")
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["total"] == 11
    second = client.get(f"/api/v1/contracts?page_size=3&page=2&snapshot={first['snapshot']}").json()
    assert not ({r["id"] for r in first["items"]} & {r["id"] for r in second["items"]})
    record = first["items"][0]
    assert isinstance(record["value"], str)
    detail = client.get("/api/v1/contracts/" + record["id"]).json()
    assert detail["provenance"][0]["sha256"]
    assert detail["value_indicator"]["status"] == "insufficient_data"
    assert client.get("/api/v1/organizations/" + record["authority_id"]).status_code == 200
    assert client.get("/api/v1/suppliers/" + record["suppliers"][0]["id"]).status_code == 200
    assert client.get("/api/v1/procurements/" + record["procurement_id"]).status_code == 200
    assert client.get("/api/v1/contracts?currency=BGN&min_value=4000000").json()["total"] == 1
    assert client.get("/api/v1/contracts?from_date=2024-01-01").json()["total"] == 0
    assert client.get("/api/v1/contracts?q=%27%20OR%201=1--").json()["total"] == 0
    stats = client.get("/api/v1/statistics/spending").json()
    assert stats["awarded_value"]["BGN"] == "5367011.180000"
    assert sum(m["contracts"] for m in stats["months"]) == stats["contracts"]
    assert client.get("/api/v1/export?currency=BGN&min_value=4000000").text.count("\n") == 2
    assert client.get("/api/v1/status").json()["notices"] == 12


@pytest.mark.parametrize(
    "url,code",
    [
        ("/api/v1/contracts?page_size=101", 422),
        ("/api/v1/contracts?sort=evil", 422),
        ("/api/v1/contracts?min_value=1", 422),
        ("/api/v1/contracts?currency=BGN&min_value=9&max_value=1", 422),
        ("/api/v1/contracts?from_date=2023-02-01&to_date=2023-01-01", 422),
        ("/api/v1/contracts/missing", 404),
        ("/api/v1/contracts?snapshot=00000000000000000000", 409),
    ],
)
def test_invalid_requests(url, code):
    response = TestClient(app).get(url)
    assert response.status_code == code, response.text
    assert "error" in response.json()


def test_public_writes_denied_and_rate_limited():
    buckets.clear()
    client = TestClient(app)
    assert client.post("/api/v1/contracts", json={}).status_code == 405
    assert client.get("/health").headers["x-content-type-options"] == "nosniff"
    for _ in range(121):
        response = client.get("/health")
    assert response.status_code == 429
    buckets.clear()


def test_import_lock():
    with engine().connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(824691)"))
        try:
            with pytest.raises(RuntimeError, match="Another import"):
                run(Path("tests/fixtures/manifest.json"))
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(824691)"))
