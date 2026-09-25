# Official-source validation — 25 September 2026

**Result: 1,015 automated comparisons passed, with no discrepancies found.** This review covers every currently indexed notice and contract. It does not certify all Bulgarian procurement, current national spending, or the truth of statements made by contracting authorities.

## Sources and method

The sole procurement source is **Tenders Electronic Daily (TED), Publications Office of the European Union**. No commercial aggregators, news articles, search snippets, generated descriptions or third-party company databases were used as evidence for the records. TED publishes procurement notices submitted by contracting authorities; it is not the Bulgarian national company register.

`scripts/audit_official_sources.py` independently downloads the 12 official XML notices and their official rendered versions. It does not call the application's transformation, identity, or calculation code. It compares the running read API and CSV against the source fields, checks original SHA-256 fingerprints, and independently reconciles totals and shares. See [machine-readable results and all source links](official-source-audit.json).

Checks cover contract/lot numbers, original titles, dates, values/currencies, bidder counts, CPV, procedures, authority and supplier names/identifiers/towns, awarded and unsuccessful outcomes, publication dates, attribution links, provenance checksums, profile membership, monthly/procedure totals, supplier-share denominators and percentages, single-bid observations and insufficient-sample states. VAT treatment is checked against the official rendered notice label. Country fields are used for identity; missing country values are now rejected rather than assumed to be Bulgarian.

## Dataset boundary

The manifest is a purposive sample selected from a TED query covering 1–7 January 2023. All 12 selected notices were published on 3 January 2023. They contain 15 outcomes: 11 awarded contracts and four unsuccessful/no-award outcomes. The award values sum to **BGN 5,367,011.18 excluding VAT**. Unsuccessful outcomes are not zero-value awarded contracts.

These are historical source amounts, not payments, actual expenditure, current company details, or national totals. Procurement titles and legal names are preserved even when the source wording appears repetitive. The audit does not silently rewrite government-published text.

## Euro correction

Bulgaria adopted the euro on **1 January 2026**. [Council Regulation (EU) 2025/1409](https://eur-lex.europa.eu/eli/reg/2025/1409/oj/eng) fixes **EUR 1 = BGN 1.95583**. The [Bulgarian National Bank's conversion and rounding guidance](https://bnb.bg/AboutUs/AUEurosystem/AUAccessionToTheEuroArea/AUAEFIQuestionsAndAnswers/POAEFI_QUESTIONSANDANS11_BG) specifies use of the complete rate and rounding to two decimal places, increasing the second decimal when the third is five or greater.

The interface now leads with a labelled EUR equivalent, followed by the original BGN amount. The total equivalent is **EUR 2,744,109.24**. Original currency/value fields are unchanged. This is a presentational conversion, not a claim that the 2022 contracts were reported or paid in euros, and not an inflation adjustment.

The frontend uses exact integer arithmetic. Each total is converted after summing the original BGN values, so summing individually rounded EUR equivalents can differ by cents. Other source currencies remain separate. Monetary search filters and CSV exports retain original source currencies and values; this is stated on the search page and in methodology.

## Other corrections

- Coverage badges now read the actual database count and dates and disclose loading/failure states.
- Supplier profiles no longer display their own filtered value as a misleading supplier-share panel. Authority shares remain explicitly limited to selected sole-supplier awards.
- Share formulas now describe their selected-record denominator accurately, including the global statistics endpoint.
- The API's row limit is described as configured, without claiming an unperformed performance verification.
- Source records, independent project calculations, and governmental findings are explicitly distinguished.

## What is not verified

Later corrections/amendments, actual payments, contract performance, supplier ownership and current company registration were not independently checked. Matching TED does not prove that an authority's source notice is free of mistakes. The data cannot support conclusions about corruption, national market share, or the current Bulgarian procurement market. Every value indicator in this small cohort lacks the required comparable sample, so none is presented as an established outlier.

The site is an independent project, not a government service. Official source notices and project calculations are intentionally labelled separately.

## Reproduction

With the local site running and Python dependencies installed, run `python scripts/audit_official_sources.py` from the repository root. The audit uses official TED HTTPS endpoints and the localhost API, paces requests, retries temporary rate limits, and writes an explicit failure list. Network failure aborts verification; it does not count as a pass. The JSON report records the verification time and all notice source URLs/checksums.

Source policy references: [TED Search API](https://docs.ted.europa.eu/api/latest/search.html), [TED reuse conditions](https://ted.europa.eu/en/legal-notice), and the [Bulgarian Public Procurement Agency's official open-data page](https://www2.aop.bg/e-uslugi/otvoreni-danni-ot-rop/). The AOP page is background about national coverage, not an additional dataset imported by this application.

## Application verification

The full local Docker website was rebuilt and checked. Four Chromium browser journeys passed, covering displayed totals and source links, filters, profiles, comparisons, exports, failure states, keyboard focus, seven-page automated accessibility checks, and mobile layout. Desktop/mobile screenshots are in `docs/screenshots/`. Automated checks are not an accessibility certification. The audit also passed the Python/importer tests (37 existing tests plus the new missing-country case), two currency test cases, static checks and production builds.
