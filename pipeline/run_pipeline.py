import argparse
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.models import IngestionRun
from pipeline.extract import download, validate_url
from pipeline.load import load
from pipeline.transform import transform


def run(manifest_path: Path, live: bool = False) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not 1 <= len(manifest["notices"]) <= 100:
        raise ValueError("Manifest must contain 1-100 notices")
    run_id = str(uuid.uuid4())
    counts = dict(seen=0, inserted=0, updated=0, unchanged=0, quarantined=0)
    with engine().connect() as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(824691)")):
            raise RuntimeError("Another import is active; retry after it completes")
        connection.commit()
        try:
            with Session(engine()) as audit:
                audit.add(
                    IngestionRun(
                        id=run_id, started_at=datetime.now(UTC), status="running", **counts
                    )
                )
                audit.commit()
            try:
                with Session(connection) as db, db.begin():
                    for item in manifest["notices"]:
                        counts["seen"] += 1
                        validate_url(item["xml_url"], resolve=live)
                        try:
                            raw = (
                                download(item["xml_url"])
                                if live
                                else (manifest_path.parent / (item["id"] + ".xml")).read_bytes()
                            )
                            checksum = hashlib.sha256(raw).hexdigest()
                            if not live and checksum != item["sha256"]:
                                raise ValueError("Cached source checksum mismatch")
                            record = transform(raw)
                            if record.id != item["id"]:
                                raise ValueError("Manifest/notice identity mismatch")
                            source_url = f"https://ted.europa.eu/bg/notice/-/detail/{record.id}"
                            retrieved = (
                                datetime.now(UTC)
                                if live
                                else datetime.fromisoformat(item["retrieved_at"])
                            )
                            counts[load(db, record, checksum, source_url, retrieved, run_id)] += 1
                        except (ValueError, OSError) as exc:
                            counts["quarantined"] += 1
                            quarantine = Path("data/quarantine")
                            quarantine.mkdir(parents=True, exist_ok=True)
                            (quarantine / f"{run_id}.json").write_text(
                                json.dumps({"notice": item["id"], "reason": str(exc)}),
                                encoding="utf-8",
                            )
                            raise
                        if live:
                            time.sleep(1)
                status, error = "success", None
            except Exception as exc:
                status, error = "failed", type(exc).__name__ + ": " + str(exc)[:200]
                counts.update(inserted=0, updated=0, unchanged=0)
            with Session(engine()) as audit:
                audit_run = audit.get(IngestionRun, run_id)
                assert audit_run is not None
                for key, value in counts.items():
                    setattr(audit_run, key, value)
                audit_run.status, audit_run.error = status, error
                audit_run.completed_at = datetime.now(UTC)
                audit.commit()
            result = {"run_id": run_id, "status": status, **counts, "error": error}
            print(json.dumps(result), flush=True)
            if status != "success":
                raise RuntimeError(error)
            return result
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(824691)"))
            connection.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/cohort/manifest.json"))
    parser.add_argument(
        "--live", action="store_true", help="Fetch official XML instead of verified local cache"
    )
    parser.add_argument(
        "--schedule", action="store_true", help="Recheck the fixed historical cohort every 24 hours"
    )
    args = parser.parse_args()
    while True:
        run(args.manifest, args.live)
        if not args.schedule:
            break
        time.sleep(86400)
