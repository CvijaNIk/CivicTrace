import { useEffect, useState } from "react";
import { filterRecords, loadDataset, type Dataset } from "./data";
type State =
  { kind: "loading" } | { kind: "error" } | { kind: "ready"; data: Dataset };
export function App({ loader = loadDataset }: { loader?: typeof loadDataset }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    const timeout = window.setTimeout(() => {
      setState({ kind: "error" });
      controller.abort();
    }, 10000);
    void loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          window.clearTimeout(timeout);
          setState({ kind: "ready", data });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          window.clearTimeout(timeout);
          setState({ kind: "error" });
        }
      });
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [loader, attempt]);
  const data = state.kind === "ready" ? state.data : null;
  const rows = data ? filterRecords(data.records, query, status) : [];
  return (
    <>
      <a className="skip" href="#main">
        Skip to research records
      </a>
      <header className="masthead">
        <a className="brand" href="#main">
          CivicTrace<span>Research workbench</span>
        </a>
        <nav aria-label="Page">
          <a href="#records">Records</a>
          <a href="#source">Source & limitations</a>
        </nav>
        <span className="local">Local preview</span>
      </header>
      <main id="main" tabIndex={-1}>
        <section className="intro" aria-labelledby="title">
          <p className="eyebrow">PROCUREMENT / INVENTED DATASET</p>
          <h1 id="title">
            Inspect the record.
            <br />
            Understand its limits.
          </h1>
          <p className="lead">
            A small, transparent starting point for evidence-led research.
            Explore invented records and trace every value back to its fixture.
          </p>
        </section>
        <aside className="notice" aria-label="Synthetic data notice">
          <strong>Synthetic records only</strong>
          <p>
            All organizations and records are invented. These examples establish
            no real procurement findings. Real analytical indicators are
            disabled (<code>analytics_enabled: false</code>).
          </p>
        </aside>
        <section id="records" aria-labelledby="records-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">01 / RECORD EXPLORER</p>
              <h2 id="records-title">Research records</h2>
            </div>
            <span className="badge">Synthetic fixture · v1</span>
          </div>
          <form
            className="filters"
            aria-label="Filter records"
            onSubmit={(e) => e.preventDefault()}
          >
            <div>
              <label htmlFor="query">
                Search identifiers or source reference
              </label>
              <input
                id="query"
                type="search"
                maxLength={128}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Try SYN-003 or SYN-SUPPLIER-1"
              />
            </div>
            <div>
              <label htmlFor="status">Bid-count availability</label>
              <select
                id="status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="all">All records</option>
                <option value="reported">Reported count</option>
                <option value="missing">Missing count</option>
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
          <p role="status" aria-live="polite">
            {state.kind === "loading"
              ? "Loading local synthetic records…"
              : state.kind === "ready"
                ? `${rows.length} of ${data?.records.length} synthetic records shown.`
                : ""}
          </p>
          {state.kind === "error" && (
            <div role="alert" className="empty">
              <h3>Could not load the synthetic dataset</h3>
              <p>
                The local file is unavailable or does not meet the supported
                data contract. No records are shown.
              </p>
              <button onClick={() => setAttempt((n) => n + 1)}>
                Try again
              </button>
            </div>
          )}
          {state.kind === "ready" &&
            (rows.length ? (
              <div
                className="table-scroll"
                role="region"
                aria-label="Synthetic procurement records"
                tabIndex={0}
              >
                <table>
                  <caption>
                    Invented records · reported bid counts are not a risk
                    assessment
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Record & source</th>
                      <th scope="col">Buyer</th>
                      <th scope="col">Supplier</th>
                      <th scope="col">Reported bids</th>
                      <th scope="col">Data status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.record_id}>
                        <th scope="row">
                          {row.record_id}
                          <small>{row.source_reference}</small>
                        </th>
                        <td>{row.buyer_id}</td>
                        <td>{row.supplier_id}</td>
                        <td>
                          {row.bid_count === null
                            ? "Unknown — not supplied"
                            : row.bid_count}
                        </td>
                        <td>
                          <span className={`pill ${row.data_status}`}>
                            {row.data_status === "missing"
                              ? "Missing count"
                              : "Reported count"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty">
                <h3>
                  {data?.records.length
                    ? "No records match these filters"
                    : "The synthetic dataset contains no records"}
                </h3>
                <p>
                  {data?.records.length
                    ? "Change the search or reset the filters to see the invented examples."
                    : "This is a valid empty dataset. No conclusions can be drawn."}
                </p>
              </div>
            ))}
          <p className="hint">
            Unknown means the fixture supplies no value. A reported zero remains
            zero. Data status describes availability, not procurement validity.
          </p>
        </section>
        <section id="source" aria-labelledby="source-title" className="source">
          <p className="eyebrow">02 / PROVENANCE & BOUNDARIES</p>
          <h2 id="source-title">Know what you are looking at</h2>
          {data ? (
            <div className="source-grid">
              <div>
                <h3>Source passport</h3>
                <dl>
                  <dt>Source</dt>
                  <dd>{data.source.name}</dd>
                  <dt>Original fixture</dt>
                  <dd>
                    <code>{data.source.path}</code>
                  </dd>
                  <dt>Original SHA-256</dt>
                  <dd className="hash">{data.source.sha256}</dd>
                  <dt>Rights & attribution</dt>
                  <dd>
                    {data.source.license} · {data.source.attribution}
                  </dd>
                  <dt>Privacy review</dt>
                  <dd>{data.source.privacy_review}</dd>
                  <dt>Contract</dt>
                  <dd>{data.schema_version}</dd>
                </dl>
                <a
                  href="data/synthetic-v1.json"
                  download="civictrace-synthetic-v1.json"
                >
                  Download synthetic preview JSON
                </a>
              </div>
              <div>
                <h3>Limits of interpretation</h3>
                <ul>
                  {data.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <p>
                  A checksum supports reproducibility; it does not authenticate
                  a publisher or prove that data is synthetic.
                </p>
              </div>
            </div>
          ) : (
            <p>
              Source metadata will appear only after the local data contract is
              validated.
            </p>
          )}
        </section>
      </main>
      <footer>
        CivicTrace · Local synthetic research preview · No accounts or uploads
      </footer>
    </>
  );
}
