import { useId } from "react";
import {
  validatePassport,
  safeSourceUrl,
  type Json,
  type Obj,
} from "./passport";
function Value({ value }: { value: Json | undefined }) {
  if (value === null || value === undefined)
    return <span>Unknown — not supplied</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ol>
        {value.map((v, i) => (
          <li key={i}>
            <Value value={v} />
          </li>
        ))}
      </ol>
    ) : (
      <span>None supplied</span>
    );
  if (typeof value === "object")
    return Object.keys(value).length ? (
      <dl>
        {Object.keys(value)
          .sort()
          .map((k) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>
                <Value value={value[k]} />
              </dd>
            </div>
          ))}
      </dl>
    ) : (
      <span>None supplied</span>
    );
  return <span>{String(value)}</span>;
}
export function PassportFinding({
  passport,
  synthetic,
}: {
  passport: unknown;
  synthetic: boolean;
}) {
  const id = useId();
  let p: Obj;
  try {
    if (synthetic !== true) throw Error("Synthetic only");
    p = validatePassport(passport);
  } catch {
    return (
      <aside role="alert" className="notice">
        Finding unavailable: unsupported, incomplete or conflicting metadata. No
        finding is verified. Synthetic preview only; analytics_enabled: false.
      </aside>
    );
  }
  const source = p.source as Obj,
    lineage = p.lineage as Obj | undefined;
  const href = safeSourceUrl(String(source.reference));
  const groups = [
    ["Methodology", p.rule],
    ["Source-reported facts — truth not independently confirmed", p.facts],
    [
      "Computation — reported result, not recalculated by this view",
      p.computation,
    ],
    ["Reference values", p.benchmark],
    ["Evidence limitations", p.limitations],
    ["Uncertainty", p.uncertainty],
    ["Derived interpretation — not an established finding", p.interpretation],
    ["Unverified allegations — not confirmed facts", p.allegations],
    [
      "Verification steps — required, not completed by this view",
      p.verification_steps,
    ],
  ] as const;
  return (
    <article className="passport source" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>Synthetic Evidence Passport finding</h2>
      <aside className="notice" aria-label="Evidence trust boundary">
        <strong>Synthetic only · analytics_enabled: false</strong>
        <p>
          No independently confirmed real-world facts. Schema validation and
          hashes do not prove truth, publisher authenticity, acquisition time,
          rights or admissibility. This view does not execute verification.
        </p>
        {!lineage && (
          <p>
            Legacy 0.1.0: expanded checksum, transformations, rights evidence
            and historical environment are unknown.
          </p>
        )}
        {lineage?.status === "legacy-incomplete" && (
          <p>
            Migrated legacy metadata is incomplete; missing evidence remains
            unknown.
          </p>
        )}
      </aside>
      <h3>Finding identity</h3>
      <Value
        value={{
          finding_id: p.finding_id ?? null,
          schema_version: p.schema_version ?? null,
        }}
      />
      <h3>Source identity and original checksum</h3>
      <Value value={source} />
      {href ? (
        <a href={href} rel="noopener noreferrer" referrerPolicy="no-referrer">
          Open source reference
        </a>
      ) : (
        <p>
          Source reference is plain text; no approved HTTP/HTTPS link is
          available.
        </p>
      )}
      {groups.map(([label, value]) => (
        <section key={label}>
          <h3>{label}</h3>
          <Value value={value} />
        </section>
      ))}
      <section>
        <h3>Data origin, transformation chain, rights and environment</h3>
        <p>
          Artifact names and pointers are references, not executable paths.
          Status describes supplied metadata; it is not a verification result.
        </p>
        <Value value={lineage} />
      </section>
    </article>
  );
}
