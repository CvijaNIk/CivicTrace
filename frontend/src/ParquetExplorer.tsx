import { useEffect, useState } from "react";
import {
  loadParquet,
  type ParquetData,
  type Field,
  emptyEntityFilters,
  matchesEntities,
  type EntityFilters,
} from "./parquet";
const filterLabels: Record<keyof EntityFilters, string> = {
  buyerId: "Buyer exact ID",
  buyerName: "Buyer name contains",
  supplierId: "Supplier / tenderer exact ID",
  supplierName: "Supplier / tenderer name contains",
  contractId: "Contract exact ID",
  contractName: "Contract title contains",
};
const show = (f: Field) =>
  f.state === "present" ? f.value : `Unknown — ${f.state}`;
export function ParquetExplorer({
  loader = loadParquet,
}: {
  loader?: typeof loadParquet;
}) {
  const [data, setData] = useState<ParquetData | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [entities, setEntities] = useState<EntityFilters>({
    ...emptyEntityFilters,
  });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError(false);
    const timer = window.setTimeout(() => {
      setError(true);
      controller.abort();
    }, 10000);
    void loader(controller.signal)
      .then((d) => {
        if (!controller.signal.aborted) {
          setData(d);
          window.clearTimeout(timer);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError(true);
          window.clearTimeout(timer);
        }
      });
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [loader, attempt]);
  const rows =
    data?.records.filter(
      (r) =>
        matchesEntities(r, entities) &&
        (status === "all" || r.release.canonical.status.value === status) &&
        [
          r.release.canonical.source_record?.ocid,
          r.release.canonical.source_id,
          r.release.source_file,
        ].some((s) => s?.toLowerCase().includes(query.trim().toLowerCase())),
    ) ?? [];
  return (
    <>
      <a className="skip" href="#main">
        Skip to snapshot records
      </a>
      <header className="masthead">
        <a className="brand" href="?">
          CivicTrace<span>Research workbench</span>
        </a>
        <a href="?">Original fixture explorer</a>
        <span className="local">Local preview</span>
      </header>
      <main id="main" tabIndex={-1}>
        <h1>Verified synthetic Parquet preview</h1>
        <aside className="notice">
          <strong>Synthetic records only</strong>
          <p>
            Invented procedures. Real indicators disabled:{" "}
            <code>analytics_enabled: false</code>. No totals, rankings or risk
            scores.
          </p>
        </aside>
        <p>
          All imported release versions. Source date offsets retained. Separate
          award and contract values are exact decimal strings; no FX or
          latest-version inference.
        </p>
        <p id="identity-help">
          Exact IDs are case-sensitive source IDs, including whitespace; names
          are case-insensitive substrings. Names never establish legal identity.
          ID and name must match the same entity; categories combine with AND.
          Supplier search covers explicitly reported suppliers/tenderers or
          award-linked parties, not all possible bidders. Counts refer to
          release records, not unique entities.
        </p>
        <form
          aria-describedby="identity-help"
          className="filters"
          onSubmit={(e) => e.preventDefault()}
        >
          <div>
            <label htmlFor="snapshot-search">Search source identifiers</label>
            <input
              id="snapshot-search"
              type="search"
              maxLength={128}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="snapshot-status">Procedure status</label>
            <select
              id="snapshot-status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="all">All statuses</option>
              {Array.from(
                new Set(
                  data?.records
                    .map((r) => r.release.canonical.status.value)
                    .filter((v): v is string => v !== null),
                ),
              )
                .sort()
                .map((s) => (
                  <option key={s}>{s}</option>
                ))}
            </select>
          </div>
          {(Object.keys(filterLabels) as (keyof EntityFilters)[]).map((key) => (
            <div key={key}>
              <label htmlFor={key}>{filterLabels[key]}</label>
              <input
                id={key}
                type="search"
                maxLength={4096}
                value={entities[key]}
                onChange={(e) =>
                  setEntities({ ...entities, [key]: e.target.value })
                }
              />
            </div>
          ))}
          <button
            type="button"
            onClick={() => {
              setEntities({ ...emptyEntityFilters });
              setQuery("");
              setStatus("all");
            }}
          >
            Reset filters
          </button>
        </form>
        <section aria-label="Active filters">
          <h2>Active filters</h2>
          {query ||
          status !== "all" ||
          Object.values(entities).some(Boolean) ? (
            <ul>
              {query && <li>Source identifiers: {query}</li>}
              {status !== "all" && <li>Procedure status: {status}</li>}
              {(Object.keys(filterLabels) as (keyof EntityFilters)[])
                .filter((key) => entities[key])
                .map((key) => (
                  <li key={key}>
                    {filterLabels[key]}:{" "}
                    <code style={{ whiteSpace: "pre-wrap" }}>
                      {entities[key]}
                    </code>
                  </li>
                ))}
            </ul>
          ) : (
            <p>No active filters.</p>
          )}
        </section>
        <p role="status">
          {data
            ? `${rows.length} of ${data.records.length} synthetic procedures shown.`
            : error
              ? ""
              : "Loading verified snapshot…"}
        </p>
        {error && (
          <div role="alert">
            <p>Snapshot unavailable or integrity/contract validation failed.</p>
            <button onClick={() => setAttempt((n) => n + 1)}>Try again</button>
          </div>
        )}
        {data && (
          <>
            {!rows.length && <p>No procedures match these filters.</p>}
            {rows.map((r) => (
              <section
                className="source"
                key={r.release.canonical.id}
                aria-label={r.release.canonical.source_record?.ocid}
              >
                <h2>{r.release.canonical.source_record?.ocid}</h2>
                <p>
                  Release: {r.release.canonical.source_id} · Status:{" "}
                  {show(r.release.canonical.status)} · Release date:{" "}
                  {show(r.release.canonical.date)}
                </p>
                {(["buyers", "suppliers", "contracts"] as const).map((kind) => (
                  <div key={kind}>
                    <h3>
                      {kind === "buyers"
                        ? "Buyer"
                        : kind === "suppliers"
                          ? "Suppliers / tenderers"
                          : "Contract identities"}
                    </h3>
                    {!r.search[kind].length && (
                      <p>Unknown — no verified {kind} available.</p>
                    )}
                    <ul>
                      {r.search[kind].map((entity, i) => (
                        <li key={i}>
                          ID:{" "}
                          <code style={{ whiteSpace: "pre-wrap" }}>
                            {show(entity.source_id)}
                          </code>{" "}
                          · {kind === "contracts" ? "Title" : "Name"}:{" "}
                          {show(entity.name)}
                          <details>
                            <summary>Identity source reference</summary>
                            <p>
                              {entity.source_file} · {entity.pointer_scope} ·{" "}
                              {entity.pointer}
                            </p>
                            <p className="hash">{entity.record_sha256}</p>
                            <p className="hash">
                              Canonical identity:{" "}
                              {entity.canonical_id ?? "Unknown — not resolved"}
                            </p>
                          </details>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
                <details>
                  <summary>Source reference and row checksum</summary>
                  <p>{r.release.source_file}</p>
                  <p className="hash">{r.release.record_sha256}</p>
                  <p className="hash">
                    Release identity: {r.release.canonical.id}
                  </p>
                </details>
                <div
                  className="table-scroll"
                  role="region"
                  aria-label="Exact synthetic values"
                  tabIndex={0}
                >
                  <table>
                    <caption>
                      Separate awards and contracts — not expenditure totals
                    </caption>
                    <thead>
                      <tr>
                        <th>Kind / source ID</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Currency</th>
                        <th>Exact projected amount</th>
                        <th>Availability / exclusion</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(["awards", "contracts"] as const).flatMap((kind) =>
                        r[kind].map((c) => (
                          <tr key={`${kind}-${c.canonical.id}`}>
                            <th scope="row">
                              {kind} / {c.canonical.source_id}
                            </th>
                            <td>{show(c.canonical.date)}</td>
                            <td>{show(c.canonical.status)}</td>
                            <td>{show(c.canonical.money!.currency)}</td>
                            <td>{c.amount ?? "Unavailable"}</td>
                            <td>
                              {c.projection_exclusion ??
                                `Amount: ${c.canonical.money!.amount.state}; currency: ${c.canonical.money!.currency.state}`}
                              {c.projection_exclusion && (
                                <>
                                  {" "}
                                  · Exact source amount:{" "}
                                  {show(c.canonical.money!.amount)}
                                </>
                              )}
                            </td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
            <section className="source">
              <h2>Snapshot provenance and coverage</h2>
              <dl>
                <dt>Snapshot identity</dt>
                <dd className="hash">{data.snapshot_id}</dd>
                <dt>Schema versions</dt>
                <dd>
                  {data.schema_version} · {data.snapshot_version} ·{" "}
                  {data.canonical_schema_version}
                </dd>
                <dt>Original gzip SHA-256</dt>
                <dd className="hash">{data.lineage.original_file_sha256}</dd>
                <dt>Expanded SHA-256</dt>
                <dd className="hash">{data.lineage.decompressed_sha256}</dd>
                <dt>Import coverage</dt>
                <dd>
                  {data.import_summary.accepted} accepted;{" "}
                  {data.import_summary.rejected} rejected of{" "}
                  {data.import_summary.rows} source rows. Excluded projections
                  remain visible above.
                </dd>
              </dl>
              <details>
                <summary>
                  Source metadata, rights and evidence inventory
                </summary>
                <pre
                  style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
                >
                  {JSON.stringify(data.lineage, null, 2)}
                </pre>
              </details>
              <details>
                <summary>
                  Import rejections, quarantine and projection exclusions
                </summary>
                <p>{data.projection_exclusions} excluded amount projections</p>
                <pre
                  style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
                >
                  {JSON.stringify(data.exclusion_ledger, null, 2)}
                </pre>
              </details>
              <ul>
                {data.limitations.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
              <a href="data/parquet-v1.json" download>
                Download verified synthetic preview JSON
              </a>
            </section>
          </>
        )}
      </main>
    </>
  );
}
