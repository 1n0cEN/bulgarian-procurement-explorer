"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Party = {
  id: string;
  name: string;
  town?: string;
  official_identifier?: string;
};
type Row = {
  id: string;
  procurement_id: string;
  title: string;
  authority_id: string;
  authority: string;
  location: string | null;
  procedure: string;
  date: string | null;
  value: string | null;
  currency: string | null;
  suppliers: Party[];
  bidders: number | null;
  source_url: string;
  source_number: string;
  lot: string | null;
  cpv: string | null;
  vat: string;
  original_value: string | null;
};
type Totals = {
  contracts: number;
  known_values: number;
  awarded_value: Record<string, string>;
  organizations: number;
  suppliers: number;
};
type Stats = Totals & {
  months: (Totals & { period: string })[];
  procedures: (Totals & { procedure: string })[];
};
type Status = {
  coverage: string;
  notices: number;
  last_success: string | null;
  freshness: string;
  publication_from: string | null;
  publication_to: string | null;
  runs: {
    id: string;
    status: string;
    seen: number;
    inserted: number;
    unchanged: number;
    quarantined: number;
    started_at: string;
  }[];
};
type Search = {
  items: Row[];
  total: number;
  page: number;
  page_size: number;
  snapshot: string;
};
type Indicator = {
  name: string;
  status: string;
  explanation: string;
  formula: string;
  sample_size: number;
  minimum_sample: number;
  algorithm_version: string;
  comparison_group: string;
  limitations: string;
  value: string | null;
  median?: string;
  mad?: string;
  threshold_value?: string;
};
type Detail = Row & {
  value_indicator: Indicator;
  provenance: {
    notice_id: string;
    publication_date: string;
    source_url: string;
    retrieved_at: string;
    sha256: string;
    run_id: string;
    transform_version: string;
  }[];
};
type Concentration = {
  formula: string;
  limitations: string;
  sample_size: number;
  excluded_contracts: number;
  denominator: Record<string, string>;
  suppliers: (Party &
    Totals & { share_percent: Record<string, string | null> })[];
};
type Profile = Party & {
  statistics: Stats;
  contracts: Row[];
  concentration: Concentration;
};
type Procurement = {
  id: string;
  title: string;
  authority_id: string;
  procedure: string;
  reference: string | null;
  contracts: Row[];
  awards: {
    id: string;
    lot: string | null;
    status: string;
    reason: string | null;
  }[];
  notices: { id: string; source_url: string; publication_date: string }[];
};

function money(value: string | null, currency: string | null) {
  if (value === null || !currency) return "Not reported";
  const [whole, fraction = ""] = value.split(".");
  return `${BigInt(whole).toLocaleString("en-GB")}${fraction && /[1-9]/.test(fraction) ? "." + fraction.replace(/0+$/, "").padEnd(2, "0") : ""} ${currency}`;
}
function dateLabel(value: string | null) {
  return value
    ? new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeZone: "UTC",
      }).format(new Date(value.slice(0, 10)))
    : "Not reported";
}
function useApi<T>(url: string) {
  const [state, setState] = useState<{ data?: T; error?: string }>({});
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/v1/${url}`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) {
          const b = await r.json();
          throw new Error(b.error || `Request failed (${r.status})`);
        }
        return r.json();
      })
      .then((data) => setState({ data }))
      .catch((e) => {
        if (e.name !== "AbortError") setState({ error: e.message });
      });
    return () => controller.abort();
  }, [url]);
  return state;
}
function State({ error }: { error?: string }) {
  return (
    <section className="state" role={error ? "alert" : "status"}>
      <span className="eyebrow">
        {error ? "DATA UNAVAILABLE" : "CONNECTING TO THE DATA"}
      </span>
      <h2>
        {error ? "We couldn’t load these records." : "Loading public records…"}
      </h2>
      <p>{error || "Retrieving verified records and calculated totals."}</p>
      {error && (
        <button onClick={() => window.location.reload()}>Try again</button>
      )}
    </section>
  );
}
function Coverage() {
  return (
    <aside className="coverage">
      <span className="dot" aria-hidden="true" />
      <strong>Historical sample</strong>
      <span>
        12 TED notices · Published 3 January 2023 · Partial coverage, not all
        Bulgarian spending
      </span>
      <Link href="/sources">About the dataset ↗</Link>
    </aside>
  );
}
function Heading({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="heading">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </div>
  );
}
function Metrics({ stats }: { stats: Totals }) {
  return (
    <div className="metrics">
      <article>
        <span>Awarded contract value</span>
        <strong className="money">
          {Object.entries(stats.awarded_value).map(([c, v]) => (
            <span key={c}>{money(v, c)}</span>
          ))}
        </strong>
        <small>
          {stats.known_values} contracts with reported values · excluding VAT
        </small>
      </article>
      <article>
        <span>Indexed contracts</span>
        <strong>{stats.contracts}</strong>
        <small>Awards with a contract number</small>
      </article>
      <article>
        <span>Contracting authorities</span>
        <strong>{stats.organizations}</strong>
        <small>With indexed awarded contracts</small>
      </article>
      <article>
        <span>Suppliers</span>
        <strong>{stats.suppliers}</strong>
        <small>Linked to indexed contracts</small>
      </article>
    </div>
  );
}
function Table({
  rows,
  caption = "Awarded contracts",
}: {
  rows: Row[];
  caption?: string;
}) {
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Contract / authority</th>
            <th scope="col">Supplier</th>
            <th scope="col">Concluded</th>
            <th scope="col" className="numeric">
              Awarded value
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                <Link
                  className="record-title"
                  href={`/contracts/${r.id}`}
                  lang="bg"
                >
                  {r.title}
                </Link>
                <Link
                  className="sub-link"
                  href={`/organizations/${r.authority_id}`}
                  lang="bg"
                >
                  {r.authority}
                </Link>
                <span className="tag">{r.procedure.replaceAll("_", " ")}</span>
              </td>
              <td>
                {r.suppliers.length
                  ? r.suppliers.map((s) => (
                      <Link
                        className="sub-link"
                        key={s.id}
                        href={`/suppliers/${s.id}`}
                        lang="bg"
                      >
                        {s.name}
                      </Link>
                    ))
                  : "Not reported"}
              </td>
              <td className="nowrap">{dateLabel(r.date)}</td>
              <td className="numeric nowrap">
                {money(r.value, r.currency)}
                <small>excl. VAT</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <section className="state">
      <h2>No matching contracts</h2>
      <p>
        Try a wider date range or remove a filter. No award does not imply a
        zero-value contract.
      </p>
      <Link href="/search">Clear filters</Link>
    </section>
  );
}
function Trends({
  stats,
  authority,
  supplier,
}: {
  stats: Stats;
  authority?: string;
  supplier?: string;
}) {
  return (
    <section className="panel">
      <div className="section-head">
        <div>
          <span className="eyebrow">BY CONTRACT CONCLUSION MONTH</span>
          <h2>Award values over time</h2>
        </div>
        <span className="tag">Derived statistics</span>
      </div>
      <p className="muted">
        Only months represented in the selected records. Missing months do not
        mean zero activity.
      </p>
      <table>
        <caption>
          Monthly award totals — links open underlying contracts
        </caption>
        <thead>
          <tr>
            <th>Month</th>
            <th>Contracts</th>
            <th>Awarded value</th>
          </tr>
        </thead>
        <tbody>
          {stats.months.map((m) => (
            <tr key={m.period}>
              <td>
                <Link
                  href={`/search?${new URLSearchParams({ ...(authority ? { authority } : {}), ...(supplier ? { supplier } : {}), from_date: m.period + "-01", to_date: m.period + "-" + new Date(Number(m.period.slice(0, 4)), Number(m.period.slice(5, 7)), 0).getDate() })}`}
                >
                  {m.period}
                </Link>
              </td>
              <td>{m.contracts}</td>
              <td>
                {Object.entries(m.awarded_value).map(([c, v]) => (
                  <div key={c} className="bar-row">
                    <span>{money(v, c)}</span>
                    <meter
                      aria-label={`${m.period} ${c} award value`}
                      value={Number(v)}
                      min={0}
                      max={Math.max(
                        1,
                        ...stats.months.map((x) =>
                          Number(x.awarded_value[c] || 0),
                        ),
                      )}
                    />
                  </div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
function Home() {
  const stats = useApi<Stats>("statistics/spending");
  const recent = useApi<Search>("contracts?page_size=5&sort=date_desc");
  const status = useApi<Status>("status");
  return (
    <>
      <div className="hero">
        <div>
          <span className="eyebrow">BULGARIA / PUBLIC PROCUREMENT</span>
          <h1>
            Follow the records.
            <br />
            <em>Understand the value.</em>
          </h1>
          <p>
            Explore who awards public contracts, who receives them, and what the
            source records actually say.
          </p>
          <form action="/search" className="hero-search">
            <label className="sr-only" htmlFor="home-query">
              Search contract, authority or supplier
            </label>
            <input
              id="home-query"
              name="q"
              placeholder="Search contracts, authorities, suppliers…"
            />
            <button>
              Explore records <span aria-hidden="true">→</span>
            </button>
          </form>
          <div className="hero-links">
            <Link href="/methodology">How to read the data ↗</Link>
            <span>No accounts. Open records.</span>
          </div>
        </div>
        <div className="hero-note">
          <span className="ledger-number">01</span>
          <span className="eyebrow">THE PUBLIC RECORD</span>
          <h2>
            Transparency starts
            <br />
            with a source.
          </h2>
          <p>
            Every contract links to its original TED notice. Every total states
            what it includes.
          </p>
          <Link href="/sources">See our data sources →</Link>
        </div>
      </div>
      <div className="page">
        <Coverage />
        {stats.data ? (
          <Metrics stats={stats.data} />
        ) : (
          <State error={stats.error} />
        )}
        <div className="section-head">
          <div>
            <span className="eyebrow">EXPLORE THE SAMPLE</span>
            <h2>Recently concluded contracts</h2>
          </div>
          <Link href="/search">View all contracts →</Link>
        </div>
        {recent.data ? (
          <Table rows={recent.data.items} />
        ) : (
          <State error={recent.error} />
        )}
        <div className="two-col">
          {stats.data && <Trends stats={stats.data} />}
          <section className="panel dark">
            <span className="eyebrow">CONTEXT MATTERS</span>
            <h2>
              Awarded value
              <br />
              is not money paid.
            </h2>
            <p>
              These records describe contract awards, not actual payments. This
              small historical sample cannot describe the whole procurement
              market.
            </p>
            <Link href="/methodology">Read the methodology →</Link>
            <p className="fine">
              Last successful import:{" "}
              {dateLabel(status.data?.last_success || null)}
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
function SearchPage({ query }: { query: string }) {
  return (
    <div className="page">
      <Heading eyebrow="THE RECORDS" title="Explore contracts">
        Search the indexed award records. Values refer to contract awards,
        excluding VAT.
      </Heading>
      <Coverage />
      {query === null ? <State /> : <SearchResults key={query} query={query} />}
    </div>
  );
}
function SearchResults({ query }: { query: string }) {
 const router=useRouter();
  const current = new URLSearchParams(query);
  const result = useApi<Search>(`contracts?${query}`);
  const orgs = useApi<{ items: Party[] }>("organizations");
  const suppliers = useApi<{ items: Party[] }>("suppliers");
  function pageLink(page: number) {
    const p = new URLSearchParams(query);
    p.set("page", String(page));
    if (result.data) p.set("snapshot", result.data.snapshot);
    return `/search?${p}`;
  }
  return (
    <>
      <form
        action="/search"
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          const p = new URLSearchParams();
          new FormData(e.currentTarget).forEach((v, k) => {
            if (String(v).trim()) p.set(k, String(v));
          });
          router.push(`/search?${p}`);
        }}
      >
        <label className="wide">
          Search
          <input
            name="q"
            defaultValue={current.get("q") || ""}
            placeholder="Title, authority or supplier"
          />
        </label>
        <label>
          Authority
          <select
            name="authority"
            defaultValue={current.get("authority") || ""}
          >
            <option value="">All authorities</option>
            {orgs.data?.items.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Supplier
          <select name="supplier" defaultValue={current.get("supplier") || ""}>
            <option value="">All suppliers</option>
            {suppliers.data?.items.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Concluded from
          <input
            type="date"
            name="from_date"
            defaultValue={current.get("from_date") || ""}
          />
        </label>
        <label>
          Concluded to
          <input
            type="date"
            name="to_date"
            defaultValue={current.get("to_date") || ""}
          />
        </label>
        <label>
          Currency
          <select name="currency" defaultValue={current.get("currency") || ""}>
            <option value="">All currencies</option>
            <option>BGN</option>
            <option>EUR</option>
          </select>
        </label>
        <label>
          Minimum value
          <input
            name="min_value"
            type="number"
            min="0"
            step="0.01"
            defaultValue={current.get("min_value") || ""}
          />
        </label>
        <label>
          Maximum value
          <input
            name="max_value"
            type="number"
            min="0"
            step="0.01"
            defaultValue={current.get("max_value") || ""}
          />
        </label>
        <label>
          Procedure
          <input
            name="procedure"
            defaultValue={current.get("procedure") || ""}
            placeholder="e.g. OPEN"
          />
        </label>
        <label>
          Authority town
          <input
            name="location"
            defaultValue={current.get("location") || ""}
            placeholder="Exact source town"
          />
        </label>
        <label>
          Order
          <select name="sort" defaultValue={current.get("sort") || "date_desc"}>
            <option value="date_desc">Newest conclusion first</option>
            <option value="date_asc">Oldest conclusion first</option>
            <option value="value_desc">Highest value first</option>
            <option value="value_asc">Lowest value first</option>
            <option value="title">Title</option>
          </select>
        </label>
        <button>Apply filters</button>
        <Link href="/search">Reset filters</Link>
        <small className="wide">
          Choose a currency when filtering or sorting by value. Dates refer to
          contract conclusion.
        </small>
      </form>
      {!result.data ? (
        <State error={result.error} />
      ) : (
        <>
          <div className="section-head">
            <p>
              <strong>{result.data.total}</strong> matching contracts
            </p>
            <a className="button secondary" href={`/api/v1/export?${query}`}>
              Download CSV ↓
            </a>
          </div>
          <Table rows={result.data.items} />
          <nav className="pagination" aria-label="Results pages">
            {result.data.page > 1 && (
              <a href={pageLink(result.data.page - 1)}>← Previous</a>
            )}
            <span>
              Page {result.data.page} of{" "}
              {Math.max(
                1,
                Math.ceil(result.data.total / result.data.page_size),
              )}
            </span>
            {result.data.page * result.data.page_size < result.data.total && (
              <a href={pageLink(result.data.page + 1)}>Next →</a>
            )}
          </nav>
        </>
      )}
    </>
  );
}
function ContractPage({ id }: { id: string }) {
  const { data: r, error } = useApi<Detail>(`contracts/${id}`);
  if (!r) return <State error={error} />;
  return (
    <div className="page">
      <Link href="/search">← Explore contracts</Link>
      <Heading eyebrow={`CONTRACT ${r.source_number}`} title={r.title} />
      <Coverage />
      <div className="two-col">
        <section className="panel">
          <span className="eyebrow">ORIGINAL RECORD</span>
          <h2>{money(r.value, r.currency)}</h2>
          <p>Reported award value · excluding VAT · not a payment</p>
          <dl>
            <dt>Authority</dt>
            <dd>
              <Link href={`/organizations/${r.authority_id}`} lang="bg">
                {r.authority}
              </Link>
            </dd>
            <dt>Supplier(s)</dt>
            <dd>
              {r.suppliers.map((s) => (
                <Link
                  className="sub-link"
                  key={s.id}
                  href={`/suppliers/${s.id}`}
                  lang="bg"
                >
                  {s.name}
                </Link>
              ))}
            </dd>
            <dt>Contract concluded</dt>
            <dd>{dateLabel(r.date)}</dd>
            <dt>Procedure</dt>
            <dd>{r.procedure}</dd>
            <dt>Lot</dt>
            <dd>{r.lot || "Not reported"}</dd>
            <dt>CPV</dt>
            <dd>{r.cpv || "Not reported"}</dd>
            <dt>Bids received</dt>
            <dd>{r.bidders ?? "Not reported"}</dd>
            <dt>Original numeric text</dt>
            <dd>{r.original_value || "Not reported"}</dd>
          </dl>
          <a className="button" href={r.source_url}>
            Open original TED notice ↗
          </a>
          <p>
            <Link href={`/procurements/${r.procurement_id}`}>
              View procurement and all award outcomes →
            </Link>
          </p>
        </section>
        <section className="panel">
          <span className="eyebrow">EXPLAINED OBSERVATIONS</span>
          <h2>What the data can tell us</h2>
          <h3>Reported single bid</h3>
          <p>
            {r.bidders === null
              ? "Bid count not reported."
              : r.bidders === 1
                ? "The source reports one bid for this award."
                : `The source reports ${r.bidders} bids for this award.`}{" "}
            This observation is not evidence of misconduct.
          </p>
          <p className="fine">
            Rule: reported tenders received = 1 · sample: this award · version
            single-bid-1.0.0
          </p>
          <hr />
          <h3>{r.value_indicator.name}</h3>
          <span className="tag">
            {r.value_indicator.status.replaceAll("_", " ")}
          </span>
          <p>{r.value_indicator.explanation}</p>
          <dl>
            <dt>Formula</dt>
            <dd>{r.value_indicator.formula}</dd>
            <dt>Eligible peers</dt>
            <dd>
              {r.value_indicator.sample_size} (minimum{" "}
              {r.value_indicator.minimum_sample})
            </dd>
            <dt>Comparison group</dt>
            <dd>{r.value_indicator.comparison_group}</dd>
            <dt>Algorithm</dt>
            <dd>{r.value_indicator.algorithm_version}</dd>
          </dl>
          <p className="fine">{r.value_indicator.limitations}</p>
        </section>
      </div>
      <section className="panel">
        <h2>Source & provenance</h2>
        {r.provenance.map((p) => (
          <details key={p.notice_id}>
            <summary>
              TED {p.notice_id} · published {dateLabel(p.publication_date)}
            </summary>
            <dl>
              <dt>Retrieved</dt>
              <dd>{p.retrieved_at}</dd>
              <dt>SHA-256</dt>
              <dd className="hash">{p.sha256}</dd>
              <dt>Import run</dt>
              <dd>{p.run_id}</dd>
              <dt>Transformation</dt>
              <dd>{p.transform_version}</dd>
            </dl>
          </details>
        ))}
      </section>
    </div>
  );
}
function Directory({ kind }: { kind: "organizations" | "suppliers" }) {
  const { data, error } = useApi<{ items: Party[] }>(kind);
  return (
    <div className="page">
      <Heading
        eyebrow="PUBLIC PROCUREMENT RELATIONSHIPS"
        title={
          kind === "organizations" ? "Contracting authorities" : "Suppliers"
        }
      >
        Entities are linked by source identifiers, never by name similarity
        alone.
      </Heading>
      <Coverage />
      {data ? (
        <div className="directory">
          {data.items.map((o) => (
            <Link className="panel" key={o.id} href={`/${kind}/${o.id}`}>
              <span className="eyebrow">{o.town || "Town not reported"}</span>
              <h2 lang="bg">{o.name}</h2>
              <p>
                National identifier: {o.official_identifier || "Not reported"}
              </p>
              <span>Explore profile →</span>
            </Link>
          ))}
        </div>
      ) : (
        <State error={error} />
      )}
    </div>
  );
}
function ProfilePage({ kind, id }: { kind: string; id: string }) {
  const { data: p, error } = useApi<Profile>(`${kind}/${id}`);
  if (!p) return <State error={error} />;
  return (
    <div className="page">
      <Link href={`/${kind}`}>← {kind}</Link>
      <Heading
        eyebrow={
          kind === "organizations" ? "CONTRACTING AUTHORITY" : "SUPPLIER"
        }
        title={p.name}
      >
        {p.town} · National identifier:{" "}
        {p.official_identifier || "Not reported"}
      </Heading>
      <Coverage />
      <Metrics stats={p.statistics} />
      <Trends
        stats={p.statistics}
        authority={kind === "organizations" ? id : undefined}
        supplier={kind === "suppliers" ? id : undefined}
      />
      <h2>Indexed contracts</h2>
      {kind === "suppliers" && (
        <p>
          Joint-award values, if present, describe the whole contract. They are
          not allocated supplier revenue.
        </p>
      )}
      <Table rows={p.contracts} />
      <div className="two-col">
        <section className="panel">
          <h2>Procedure distribution</h2>
          <table>
            <caption>Contracts by procedure</caption>
            <thead>
              <tr>
                <th>Procedure</th>
                <th>Contracts</th>
              </tr>
            </thead>
            <tbody>
              {p.statistics.procedures.map((x) => (
                <tr key={x.procedure}>
                  <td>
                    <Link
                      href={`/search?${new URLSearchParams({ [kind === "organizations" ? "authority" : "supplier"]: id, procedure: x.procedure })}`}
                    >
                      {x.procedure}
                    </Link>
                  </td>
                  <td>{x.contracts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel">
          <h2>Sole-supplier value shares</h2>
          <p>{p.concentration.formula}</p>
          <p className="fine">
            Eligible contracts: {p.concentration.sample_size}; excluded:{" "}
            {p.concentration.excluded_contracts}. Selected sample only.
          </p>
          {p.concentration.suppliers.map((s) => (
            <p key={s.id}>
              <Link href={`/suppliers/${s.id}`}>{s.name}</Link> —{" "}
              {Object.entries(s.share_percent)
                .map(([c, v]) => `${v ?? "Undefined"}% (${c})`)
                .join(", ")}
            </p>
          ))}
          <p className="fine">{p.concentration.limitations}</p>
        </section>
      </div>
    </div>
  );
}
function ProcurementPage({ id }: { id: string }) {
  const { data: p, error } = useApi<Procurement>(`procurements/${id}`);
  if (!p) return <State error={error} />;
  return (
    <div className="page">
      <Heading eyebrow="PROCUREMENT" title={p.title} />
      <Coverage />
      <p>
        Source reference: {p.reference || "Not reported"} · Procedure:{" "}
        {p.procedure}
      </p>
      <Link href={`/organizations/${p.authority_id}`}>Authority profile →</Link>
      <h2>Award outcomes</h2>
      {p.awards.map((a) => (
        <div className="panel" key={a.id}>
          <strong>{a.status.replaceAll("_", " ")}</strong>
          <p>Lot: {a.lot || "Not reported"}</p>
          {a.reason && <p>Source reason code: {a.reason}</p>}
        </div>
      ))}
      <Table rows={p.contracts} />
      {p.notices.map((n) => (
        <p key={n.id}>
          <a href={n.source_url}>TED {n.id} ↗</a> ·{" "}
          {dateLabel(n.publication_date)}
        </p>
      ))}
    </div>
  );
}
function Sources() {
  const { data: s, error } = useApi<Status>("status");
  return (
    <div className="page">
      <Heading
        eyebrow="PROVENANCE & COVERAGE"
        title="Know where the data comes from"
      >
        Official source records, with a visible boundary around what we have
        indexed.
      </Heading>
      <Coverage />
      <section className="panel">
        <span className="eyebrow">OFFICIAL EUROPEAN UNION SOURCE</span>
        <h2>Tenders Electronic Daily</h2>
        <p>
          Publisher: Publications Office of the European Union. The fixed cohort
          contains 12 original Bulgarian F03 notices encountered in a search for
          1–7 January 2023. All selected notices were published on 3 January
          2023.
        </p>
        <p>
          These are legacy award notices, including unsuccessful outcomes. They
          do not cover every Bulgarian procurement, later amendments, or actual
          payments.
        </p>
        <p>
          <a href="https://docs.ted.europa.eu/api/latest/search.html">
            Search API documentation ↗
          </a>{" "}
          ·{" "}
          <a href="https://ted.europa.eu/en/legal-notice">
            Source reuse terms ↗
          </a>
        </p>
        <p>
          Notices may generally be reused under TED’s stated conditions.
          Third-party and personal-data rights may require additional review. No
          contact emails or phone numbers are displayed.
        </p>
      </section>
      {!s ? (
        <State error={error} />
      ) : (
        <section className="panel">
          <h2>Import status</h2>
          <p>
            <strong>{s.freshness.replaceAll("_", " ")}</strong> · Last
            successful import: {dateLabel(s.last_success)} · {s.notices} notices
            indexed
          </p>
          <p>
            Freshness describes our source check, not recent procurement
            coverage.
          </p>
          <table>
            <caption>Recent import runs</caption>
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Seen</th>
                <th>Inserted</th>
                <th>Unchanged</th>
                <th>Quarantined</th>
              </tr>
            </thead>
            <tbody>
              {s.runs.map((r) => (
                <tr key={r.id}>
                  <td>{dateLabel(r.started_at)}</td>
                  <td>{r.status}</td>
                  <td>{r.seen}</td>
                  <td>{r.inserted}</td>
                  <td>{r.unchanged}</td>
                  <td>{r.quarantined}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
function Methodology() {
  return (
    <div className="page prose">
      <Heading eyebrow="METHODS & LIMITATIONS" title="Evidence with context." />
      <p className="lead">
        This explorer makes public procurement records easier to inspect. It
        does not determine whether anyone has acted improperly.
      </p>
      {[
        [
          "01 / What a total means",
          "Monetary totals sum unique awarded contracts, once per stable source contract identity, separately for each original currency. They exclude VAT. They are not actual payments. No currency conversion is performed. Missing values are excluded, not replaced with zero.",
        ],
        [
          "02 / What is covered",
          "The initial cohort contains 12 original Bulgarian TED F03 notices published on 3 January 2023, with 15 award outcomes and 11 contracts. It is a small purposive sample, not a statistically representative picture of Bulgaria. Later changes, amendments and payments are not tracked. Dates in search are contract conclusion dates.",
        ],
        [
          "03 / Relationships and identity",
          "Authorities and suppliers are matched using source national identifiers and country. Missing identifiers remain notice-local identities. Similar names are never automatically merged. Joint awards retain all named suppliers; their value is counted once in global totals. Supplier profiles may overlap for joint awards, so their totals must not be added together.",
        ],
        [
          "04 / Statistical observations",
          "Single-bid observations reflect the source’s reported count. Value comparisons require at least 10 other contracts with the same CPV division, procedure, currency and conclusion year. The rule is value > median + 3 × 1.4826 × median absolute deviation. Missing values, missing grouping fields, and zero dispersion produce no flag.",
        ],
        [
          "05 / Supplier shares",
          "Supplier shares divide sole-supplier award value by eligible sole-supplier value within the selected authority and currency. Joint awards and missing amounts are excluded, and the denominator is disclosed. Small samples make these figures unstable. A high share does not imply misconduct.",
        ],
        [
          "06 / Reuse, privacy and corrections",
          "Exports include filtered contract fields with attribution links. Contact details are not displayed. Source notices can contain errors; follow the original notice for authoritative wording. Corrections require operator review and a new verified import. The deployment operator must publish a contact route and finish privacy review before public release.",
        ],
        [
          "07 / Accessibility",
          "The interface uses semantic tables, labeled controls, keyboard-accessible links and visible focus. Charts also present their numeric values in tables. Accessibility findings and remaining manual checks are recorded in the repository; no certification is claimed.",
        ],
      ].map(([title, body]) => (
        <section key={title}>
          <h2>{title}</h2>
          <p>{body}</p>
        </section>
      ))}
    </div>
  );
}
function Compare() {
  const orgs = useApi<{ items: Party[] }>("organizations");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  return (
    <div className="page">
      <Heading eyebrow="SIDE BY SIDE" title="Compare authorities">
        Same indexed cohort. Separate currency totals. Unequal coverage can
        explain differences.
      </Heading>
      <Coverage />
      <div className="two-col">
        {[0, 1].map((i) => (
          <section className="panel" key={i}>
            <label>
              Authority {i === 0 ? "A" : "B"}
              <select
                value={i === 0 ? a : b}
                onChange={(e) => (i === 0 ? setA : setB)(e.target.value)}
              >
                <option value="">Choose an authority</option>
                {orgs.data?.items.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </label>
            {(i === 0 ? a : b) ? (
              <Comparison key={i === 0 ? a : b} id={i === 0 ? a : b} />
            ) : (
              <p>Select an authority to inspect its indexed award totals.</p>
            )}
          </section>
        ))}
      </div>
      <p>
        Denominator: unique contracts linked to each authority in this
        historical sample. This comparison does not control for organization
        size or purchasing needs.
      </p>
    </div>
  );
}
function Comparison({ id }: { id: string }) {
  const { data, error } = useApi<Profile>(`organizations/${id}`);
  return data ? (
    <>
      <h2>{data.name}</h2>
      <p>
        <strong>{data.statistics.contracts}</strong> indexed contracts;{" "}
        {data.statistics.known_values} with reported value.
      </p>
      {Object.entries(data.statistics.awarded_value).map(([c, v]) => (
        <h3 key={c}>{money(v, c)}</h3>
      ))}
      <Link href={`/organizations/${id}`}>Inspect underlying records →</Link>
    </>
  ) : (
    <State error={error} />
  );
}
export default function Explorer({
  path,
  query,
}: {
  path: string[];
  query: string;
}) {
  const [section, id] = path;
  switch (section) {
    case undefined:
      return <Home />;
    case "search":
      return <SearchPage query={query} />;
    case "contracts":
      return id ? <ContractPage id={id} /> : <SearchPage query={query} />;
    case "procurements":
      return id ? <ProcurementPage id={id} /> : <SearchPage query={query} />;
    case "organizations":
    case "suppliers":
      return id ? (
        <ProfilePage kind={section} id={id} />
      ) : (
        <Directory kind={section} />
      );
    case "sources":
      return <Sources />;
    case "methodology":
      return <Methodology />;
    case "compare":
      return <Compare />;
    default:
      return (
        <div className="page">
          <h1>Page not found</h1>
          <Link href="/">Return home</Link>
        </div>
      );
  }
}
