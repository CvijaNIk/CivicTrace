import { useEffect, useState } from "react";
import { loadSubmission, type SubmissionReport } from "./submission";
const shown = (value: string | null) =>
  value === null ? "Unknown — not computed" : value;
export function SubmissionPeriodView({
  loader = loadSubmission,
}: {
  loader?: typeof loadSubmission;
}) {
  const [data, setData] = useState<SubmissionReport | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
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
  return (
    <>
      <a className="skip" href="#main">
        Skip to submission periods
      </a>
      <header className="masthead">
        <a className="brand" href="?">
          CivicTrace
        </a>
        <nav aria-label="Page">
          <a href="?view=parquet">Parquet records</a>
          <a href="?view=passport">Finding previews</a>
        </nav>
      </header>
      <main id="main" tabIndex={-1} className="submission">
        <div className="intro">
          <h1>Synthetic submission periods</h1>
          <p>
            Ten controlled invented records. Read-only results from the existing
            Python calculation.
          </p>
        </div>
        <aside className="notice">
          <strong>
            Invented test references — no legal or corruption finding
          </strong>
          <p>
            The 24 and 72 hour references are fictional test parameters, not
            legal deadlines or empirical peer benchmarks. Below a reference does
            not establish an irregularity, legal violation or corruption. No
            Evidence Passport findings are issued.
          </p>
          <p>
            <code>analytics_enabled: false</code>. No real DNCP analysis.
          </p>
        </aside>
        {error ? (
          <div role="alert">
            <p>
              Unable to verify the controlled synthetic report. No results
              displayed.
            </p>
            <button onClick={() => setAttempt((a) => a + 1)}>Try again</button>
          </div>
        ) : !data ? (
          <p role="status">Verifying controlled synthetic report…</p>
        ) : (
          <>
            <section aria-labelledby="population">
              <h2 id="population">Population and exclusions</h2>
              <dl className="metrics">
                <dt>Total records</dt>
                <dd>{data.denominators.total_records}</dd>
                <dt>Valid durations</dt>
                <dd>{data.denominators.valid_duration_records}</dd>
                <dt>Comparable records</dt>
                <dd>{data.denominators.comparison_records}</dd>
                <dt>Excluded from comparison</dt>
                <dd>{data.denominators.excluded_records}</dd>
              </dl>
              <p>
                Comparison counts among comparable records only: below{" "}
                {data.comparison_counts.below}, equal{" "}
                {data.comparison_counts.equal}, above{" "}
                {data.comparison_counts.above}.
              </p>
              <ul>
                {Object.entries(data.exclusions).map(([reason, count]) => (
                  <li key={reason}>
                    {reason}: {count}
                  </li>
                ))}
              </ul>
              <p>
                One primary exclusion per record. Date exclusions take
                precedence; a valid duration can still lack a reference. Unknown
                values remain unknown; equal instants retain a valid zero.
              </p>
            </section>
            <section aria-labelledby="method">
              <h2 id="method">Time and comparison basis</h2>
              <p>
                {data.time_basis}. Calendar days are elapsed 24-hour units, not
                inclusive local dates or working days.
              </p>
              <p>
                Working days: not computed — no local calendar. No holiday or
                statutory extension assumptions.
              </p>
              <ul>
                {data.limitations.map((l) => (
                  <li key={l}>{l}</li>
                ))}
              </ul>
            </section>
            <section aria-labelledby="records">
              <h2 id="records">Record details</h2>
              {data.results.map((r, i) => (
                <article
                  className="period-record"
                  key={r.record_id}
                  aria-labelledby={`record-${i}`}
                >
                  <h3 id={`record-${i}`}>{r.record_id}</h3>
                  <div className="period-columns">
                    <section className="period-facts" aria-label="Source facts">
                      <h4>Facts in invented source</h4>
                      <dl>
                        <dt>Original start</dt>
                        <dd>
                          {r.original_dates.tender_start ??
                            `Unknown — ${r.field_states.tender_start}`}
                        </dd>
                        <dt>Start field state</dt>
                        <dd>{r.field_states.tender_start}</dd>
                        <dt>Original end</dt>
                        <dd>
                          {r.original_dates.tender_end ??
                            `Unknown — ${r.field_states.tender_end}`}
                        </dd>
                        <dt>End field state</dt>
                        <dd>{r.field_states.tender_end}</dd>
                        <dt>Source reference</dt>
                        <dd>{r.source_reference}</dd>
                        <dt>Original pointer</dt>
                        <dd>{r.original_pointer}</dd>
                        {Object.entries(r.group).map(([k, v]) => (
                          <div key={k}>
                            <dt>{k}</dt>
                            <dd>{v ?? "Unknown — group not supplied"}</dd>
                          </div>
                        ))}
                      </dl>
                    </section>
                    <section
                      className="period-assumptions"
                      aria-label="Synthetic assumptions"
                    >
                      <h4>Synthetic assumptions</h4>
                      {r.benchmark ? (
                        <dl>
                          <dt>Selected reference</dt>
                          <dd>{r.benchmark.id}</dd>
                          <dt>Invented reference hours</dt>
                          <dd>{r.benchmark.elapsed_hours}</dd>
                          <dt>Basis</dt>
                          <dd>{r.benchmark.basis}</dd>
                          <dt>Reference description</dt>
                          <dd>{r.benchmark.reference}</dd>
                        </dl>
                      ) : (
                        <p>Unknown — no matching reference. No fallback.</p>
                      )}
                    </section>
                    <section
                      className="period-results"
                      aria-label="Computed comparison"
                    >
                      <h4>Computed comparison</h4>
                      <dl>
                        <dt>Period state</dt>
                        <dd>{r.period_state}</dd>
                        <dt>Elapsed hours</dt>
                        <dd>{shown(r.elapsed_hours)}</dd>
                        <dt>Calendar days</dt>
                        <dd>{shown(r.calendar_days)}</dd>
                        <dt>Signed deviation hours (duration − reference)</dt>
                        <dd>{shown(r.deviation_hours)}</dd>
                        <dt>Relation</dt>
                        <dd>{r.relation ?? "Not compared"}</dd>
                        <dt>Comparison state</dt>
                        <dd>{r.comparison_state}</dd>
                        <dt>Exclusion reason</dt>
                        <dd>{r.exclusion_reason ?? "None — compared"}</dd>
                      </dl>
                    </section>
                  </div>
                </article>
              ))}
            </section>
            <section className="source" aria-labelledby="integrity">
              <h2 id="integrity">Integrity and provenance</h2>
              <p>
                SHA-256 verifies reviewed bytes, not factual truth, source
                authenticity or legal validity. Results are replayed during
                build checks; the browser does not recalculate them.
              </p>
              <dl>
                <dt>Source SHA-256</dt>
                <dd className="hash">{data.input_sha256}</dd>
                <dt>Configuration version</dt>
                <dd>{data.configuration.version}</dd>
                <dt>Configuration SHA-256</dt>
                <dd className="hash">{data.configuration_sha256}</dd>
                {Object.entries(data.implementation_sha256).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k} implementation SHA-256</dt>
                    <dd className="hash">{v}</dd>
                  </div>
                ))}
                <dt>Rights / privacy (invented source metadata)</dt>
                <dd>
                  <pre>{JSON.stringify(data.rights, null, 2)}</pre>
                </dd>
              </dl>
            </section>
          </>
        )}
      </main>
    </>
  );
}
