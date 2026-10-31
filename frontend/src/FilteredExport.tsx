import { useEffect, useState } from "react";
import { buildExport, type ExportFilters } from "./exports";
import type { ParquetData } from "./parquet";
export function FilteredExport({
  data,
  filters,
  ids,
}: {
  data: ParquetData;
  filters: ExportFilters;
  ids: string[];
}) {
  const [links, setLinks] = useState<{ name: string; url: string }[]>([]);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    const urls: string[] = [];
    void buildExport(data, filters, ids)
      .then((bundle) => {
        if (!active) return;
        const next = (["json", "csv", "manifest"] as const).map((kind) => {
          const name =
            kind === "manifest" ? "manifest.json" : `results.${kind}`;
          const url = URL.createObjectURL(
            new Blob([bundle[kind]], {
              type:
                kind === "csv"
                  ? "text/csv;charset=utf-8"
                  : "application/json;charset=utf-8",
            }),
          );
          urls.push(url);
          return { name, url };
        });
        setLinks(next);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [data, filters, ids]);
  return (
    <section aria-label="Filtered export">
      <h2>Export current search results</h2>
      <p>
        Save results and the linked manifest together. CSV cells contain JSON
        values: decode each cell as JSON to retain exact text, decimals and
        unknown states. Synthetic evidence only.
      </p>
      {error ? (
        <p role="alert">
          Export unavailable: size limit or consistency validation failed.
        </p>
      ) : links.length ? (
        <ul>
          {links.map((link) => (
            <li key={link.name}>
              <a href={link.url} download={link.name}>
                Download filtered {link.name}
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p>Preparing filtered export…</p>
      )}
    </section>
  );
}
