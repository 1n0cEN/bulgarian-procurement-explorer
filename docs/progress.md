# Development status

Updated 25 September 2026. The application runs locally with Docker Compose. It is a work in progress, not a production-ready release. No public hosting deployment has been made.

## Implemented

- Next.js, React and TypeScript frontend with contract search, authority and supplier profiles, comparisons, source links and CSV exports.
- FastAPI read API, PostgreSQL data model and transactional TED XML importer with duplicate protection.
- Exact EUR equivalents alongside original historical BGN values, with original-currency filters and exports.
- Live coverage metadata and explanatory limitations for totals and statistical observations.

## Data and verification

The fixed historical sample contains 12 original Bulgarian TED F03 notices published on 3 January 2023: 15 award outcomes and 11 awarded contracts. Original values total BGN 5,367,011.18 excluding VAT, equivalent to EUR 2,744,109.24 at the official conversion rate.

The independent source audit passed 1,015 comparisons against official TED XML and rendered notices. See [validation report](validation-report.md) and [machine-readable evidence](official-source-audit.json) for sources, methods and scope.

Verification completed:

- All 37 existing Python and PostgreSQL tests, plus the added missing-country regression test.
- Two exact-currency test cases, Python and TypeScript static checks, and production Docker builds.
- Four Chromium browser journeys covering navigation, filters, profiles, comparisons, exports and unavailable-data states.
- Automated accessibility checks on seven pages, keyboard focus and mobile overflow checks. Desktop and mobile screenshots are available in `screenshots/`.

Automated checks are not an accessibility certification or a guarantee that source notices contain no errors. The source audit does not cover later amendments, payments, contract performance, current company registration or national procurement completeness.

## Remaining release work

- Demonstrate backup restoration and complete operational monitoring.
- Add continuous integration and complete security and privacy review.
- Finish outstanding product requirements and deployment documentation.
- Establish an operator contact and corrections process before public hosting.

## Local operation

Follow the [README](../README.md) for setup. The base Compose configuration exposes only the website on localhost:3000; PostgreSQL remains on the internal container network. The optional development override exposes PostgreSQL on localhost:55432.

Keep credentials, raw source downloads, database backups and generated caches outside version control. Test fixtures are sanitized; the source manifest retains attribution and checksums.
