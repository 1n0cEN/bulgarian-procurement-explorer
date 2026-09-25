# BG Transparency Explorer

Work in progress: an independent explorer of Bulgarian procurement award records from Tenders Electronic Daily (TED). Award values are not payments. Statistical observations are not evidence of misconduct.

## Current status

- Official sample retrieved and imported into PostgreSQL: 12 notices, 15 award outcomes, 11 contracts, BGN 5,367,011.18 reported award value excluding VAT.
- Repeated live import: 12 unchanged notices, no duplicates.
- 37 Python/domain and real-PostgreSQL tests passed, plus a new missing-country regression test and two exact-currency test cases.
- Next.js production build and both application Docker image builds passed.
- All four Chromium browser journeys passed, including automated accessibility and mobile checks.
- Full local Compose startup verified. Official-source audit: 1,015 comparisons passed across all 12 notices and 11 contracts. [Validation report](docs/validation-report.md).
- The UI displays EUR equivalents at EUR 1 = BGN 1.95583, retaining original BGN values; filters and exports use source currencies.
- Backup restoration, comprehensive security/accessibility verification, CI, and the remaining product documentation are not complete. This is not a production-ready release. Nothing has been deployed publicly.

## Structure

`frontend/`: Next.js/React/TypeScript website. `backend/`: FastAPI read API and SQLAlchemy models. `pipeline/`: strict TED XML adapter and transactional importer. `database/`: Alembic migration. `tests/`: deterministic sanitized fixtures and PostgreSQL tests. `infrastructure/`: Docker configuration. `docs/`: progress and available evidence.

## Local startup

Requires Docker Desktop running Linux containers.

1. Copy `.env.example` to `.env`. Replace both password placeholders with distinct long random values containing URL-safe characters. Keep `POSTGRES_DB=bg_transparency` for the current initialization script.
2. Run `docker compose up --build -d`.
3. Run `docker compose --profile ingestion run --rm worker python -m pipeline.run_pipeline --live` to import the fixed historical cohort from TED.
4. Open http://localhost:3000.

PostgreSQL persists in a named Docker volume and is not published to a host port by the base configuration. The optional development override publishes it only to localhost:55432. Do not run `docker compose down -v` unless you intend to delete the database.

The read API is at `/api/v1/` through the website. The API service also supplies `/docs`, `/openapi.json`, `/health`, and `/ready` internally. The public API does not allow writes.

## Tests

Install Python dependencies from `requirements.lock` in an isolated Python 3.13 environment, and run `python -m pytest tests/test_domain.py`. For the integration tests, set `TEST_DATABASE_URL` to a dedicated PostgreSQL database named `bg_test`; these tests recreate its application tables. Never point it at your data database.

In `frontend/`, run `npm ci`, `npm run lint`, `npm run typecheck`, and `npm run build`. Browser tests require the website and API to be running: `npx playwright install chromium`, then `npm test`.

## Source, privacy, and repository contents

Publisher: Publications Office of the European Union. Source documentation: https://docs.ted.europa.eu/api/latest/search.html. Reuse terms: https://ted.europa.eu/en/legal-notice. The cohort is a purposive historical sample, not national coverage. The checked-in manifest records source URLs, retrieval timestamps, and checksums. Tests use transformed XML fixtures with contact/address fields and unused prose removed; they are not raw original downloads.

Local secrets (`.env`), raw downloads, database volumes, generated caches, installed dependencies, and browser traces are intentionally excluded from Git. Software uses the MIT license; that license does not relicense the source notices or any third-party data.
