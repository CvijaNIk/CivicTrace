import example from "./passport-example.json";
import { PassportFinding } from "./PassportFinding";
export function PassportPreview() {
  return (
    <>
      <a className="skip" href="#main">
        Skip to findings
      </a>
      <header className="masthead">
        <a className="brand" href="?">
          CivicTrace
        </a>
        <nav aria-label="Page">
          <a href="?view=parquet">Parquet records</a>
          <a href="?">Original records</a>
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <h1>Synthetic finding previews</h1>
        <p>
          Four contract examples: legacy, migrated incomplete, and two complete
          synthetic passports. The first three describe the same invented
          finding for compatibility review, not three separate findings.
        </p>
        {example.findings.map((passport, i) => (
          <PassportFinding
            key={i}
            passport={passport}
            synthetic={example.synthetic && example.analytics_enabled === false}
          />
        ))}
      </main>
    </>
  );
}
