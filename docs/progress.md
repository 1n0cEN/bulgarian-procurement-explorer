# Progress and handoff

Build in progress, 25 September 2026. No public deployment.

Read full pasted request and reference specification. Workspace sources are untouched.
Official TED Search API and XML retrieval verified. Fixed cohort manifest lists 12 original Bulgarian F03 notices, all published 2023-01-03. Raw originals are ignored by Git. First independent reconciliation: 15 outcomes, 11 contracts, BGN 5,367,011.18.

Implemented normalized PostgreSQL models, strict XML adapter, fixed-origin downloader, transactional importer, read API, frontend pages and initial Compose. Python unit and PostgreSQL integration checks, browser checks, security scans, documentation and operations verification remain in progress.

Docker Desktop installed by user and verified running (per-user binary under AppData/Local/Programs/DockerDesktop/resources/bin). Prepend that directory to PATH for credential helper. PostgreSQL 18.6 container started on localhost:55432 for development; base Compose has no database port. Generated credentials in ignored .env. Never print them.

Verified subsequently: migration and source-cache import passed; repeat live import returned 12 unchanged notices; all 37 Python/PostgreSQL tests passed; Next.js build and both Docker application images built. ESLint 10 required @eslint/compat for Next plugin compatibility. Python type checks passed.

Browser checks failed: local API requests timed out. Local API and frontend processes were stopped before trying full Compose; approval review hit a usage limit, so full startup was not executed. Browser tests and accessibility checks are not passing evidence. Backup restoration remains untested. Comprehensive docs, requirement matrix, CI, monitoring, and release work remain unfinished.

Relocation requested to Documents/BG project but not completed: enumeration encountered a Windows permission error on .pytest_cache. Application source remains here; protected synced sources are a separate sibling directory. User subsequently requested a GitHub repository. Publish only tracked source and sanitized fixtures, never .env, raw downloads or caches.

Next: verify full Compose startup; resolve browser failures; demonstrate restore; complete requirement dispositions and release report. Do not claim completion before evidence is recorded.

## Official-source audit update — 25 September 2026

Full Compose now runs successfully at localhost:3000. The source audit independently fetched all 12 original TED XML notices and rendered official pages. All 1,015 comparisons passed: 15 outcomes, 11 contracts, original BGN 5,367,011.18; presentational EUR equivalent 2,744,109.24. See validation-report.md and official-source-audit.json for complete scope, links and limitations.

EUR display preserves original source BGN amounts, uses the full official rate and exact integer rounding, and clearly distinguishes derived equivalents from source facts. Coverage badges now use live database metadata. Supplier-profile shares were removed to avoid a misleading self-denominator; authority and selected-cohort share arithmetic was independently reconciled. Missing party countries are rejected rather than invented.

All 37 existing backend/PostgreSQL tests passed in an isolated bg_test container run; the added missing-country regression also passed. Currency tests, Ruff, mypy, TypeScript, ESLint and Docker builds passed. Initial browser verification uncovered a test locator mismatch and a real contrast issue; both were corrected before the final rerun. Prior notes about failed local API startup are historical and superseded.

No public hosting deployment or local relocation was performed during this audit. Remaining release work from the original build includes backup restore, CI, comprehensive operational/security review and remaining requirements; the source audit does not certify production readiness.

Final browser rerun: all four Chromium journeys passed, including seven-page axe checks, keyboard focus and mobile overflow checks. Screenshots inspected. A mobile monthly-table overflow discovered in verification was fixed with an accessible scrolling region.
