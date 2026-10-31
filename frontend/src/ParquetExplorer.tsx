import { useEffect, useState } from "react";
import { loadParquet, type ParquetData, type Field } from "./parquet";
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
        <form className="filters" onSubmit={(e) => e.preventDefault()}>
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
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setStatus("all");
            }}
          >
            Reset filters
          </button>
        </form>
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
