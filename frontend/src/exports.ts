import {
  parseParquet,
  matchesEntities,
  type ParquetData,
  type EntityFilters,
} from "./parquet";
import pin from "./parquet-pin.json";
export interface ExportFilters {
  query: string;
  status: string;
  entities: EntityFilters;
}
export function selectRecords(data: ParquetData, f: ExportFilters) {
  return data.records.filter(
    (r) =>
      matchesEntities(r, f.entities) &&
      (f.status === "all" || r.release.canonical.status.value === f.status) &&
      [
        r.release.canonical.source_record?.ocid,
        r.release.canonical.source_id,
        r.release.source_file,
      ].some((s) => s?.toLowerCase().includes(f.query.trim().toLowerCase())),
  );
}
// Sorted object keys; arrays retain verified source order. No clock/random values.
export function canonicalJSON(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJSON).join(",")}]`;
  if (value !== null && typeof value === "object")
    return `{${Object.keys(value)
      .sort()
      .map(
        (k) =>
          `${JSON.stringify(k)}:${canonicalJSON((value as Record<string, unknown>)[k])}`,
      )
      .join(",")}}`;
  const result = JSON.stringify(value);
  if (result === undefined) throw Error("Unsupported export value");
  return result;
}
// RFC4180 quoting alone does NOT stop formulas. JSON text tokens start with a
// literal double quote; nested data starts with [/{. This also prevents numeric
// coercion without changing source values. Decode CSV, then JSON.parse each cell.
export function csvCell(value: unknown): string {
  return `"${canonicalJSON(value).replaceAll('"', '""')}"`;
}
export const MAX_EXPORT_BYTES = 262144; // combined UTF-8 including manifest
const size = (s: string) => new TextEncoder().encode(s).byteLength;
export function enforceExportLimit(...files: string[]) {
  if (files.reduce((n, file) => n + size(file), 0) > MAX_EXPORT_BYTES)
    throw Error("Export byte limit exceeded");
}
export async function sha256(s: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)),
    ),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
}
export async function buildExport(
  data: ParquetData,
  filters: ExportFilters,
  displayedIds: string[],
) {
  // Clone and validate before awaiting, preventing mutable-input races.
  const checked = parseParquet(canonicalJSON(data));
  const f: ExportFilters = JSON.parse(canonicalJSON(filters));
  if (
    Object.keys(f).sort().join() !== "entities,query,status" ||
    typeof f.query !== "string" ||
    f.query.length > 128 ||
    typeof f.status !== "string" ||
    f.status.length > 4096 ||
    Object.keys(f.entities).sort().join() !==
      "buyerId,buyerName,contractId,contractName,supplierId,supplierName" ||
    Object.values(f.entities).some(
      (v) => typeof v !== "string" || v.length > 4096,
    )
  )
    throw Error("Invalid export filters");
  const records = selectRecords(checked, f);
  const ids = records.map((r) => r.release.canonical.id);
  if (canonicalJSON(ids) !== canonicalJSON(displayedIds))
    throw Error("Displayed/exported records differ");
  const columns = [
    "release_id",
    "source_id",
    "ocid",
    "source_file",
    "record_sha256",
    "release",
    "search",
    "awards",
    "contracts",
  ];
  const csv =
    columns.join(",") +
    "\r\n" +
    records
      .map(
        (r) =>
          [
            r.release.canonical.id,
            r.release.canonical.source_id,
            r.release.canonical.source_record!.ocid,
            r.release.source_file,
            r.release.record_sha256,
            r.release,
            r.search,
            r.awards,
            r.contracts,
          ]
            .map(csvCell)
            .join(",") + "\r\n",
      )
      .join("");
  const json =
    canonicalJSON({
      schema_version: "civictrace-filtered-records/1",
      synthetic: true,
      analytics_enabled: false,
      snapshot_id: checked.snapshot_id,
      records,
    }) + "\n";
  enforceExportLimit(csv, json);
  const manifest =
    canonicalJSON({
      schema_version: "civictrace-export-manifest/1",
      synthetic: true,
      analytics_enabled: false,
      snapshot_id: checked.snapshot_id,
      schema_versions: {
        preview: checked.schema_version,
        snapshot: checked.snapshot_version,
        canonical: checked.canonical_schema_version,
        records: "civictrace-filtered-records/1",
        csv: "civictrace-json-cells/1",
      },
      verified_preview: { path: "data/parquet-v1.json", sha256: pin.sha256 },
      filters: f,
      result_count: records.length,
      record_ids: ids,
      ordering:
        "Verified source order; sorted JSON keys; UTF-8; JSON LF, CSV CRLF; no BOM/timestamp",
      files: {
        "results.json": { sha256: await sha256(json), bytes: size(json) },
        "results.csv": { sha256: await sha256(csv), bytes: size(csv) },
      },
      csv: {
        columns,
        codec:
          "RFC4180 then JSON.parse each data cell; literal JSON string quotes prevent formulas and numeric coercion; arrays retain children, empty arrays mean no verified entities; field state/null retained",
        record_count_unit:
          "release records, not unique entities or financial totals",
      },
      lineage: checked.lineage,
      import_summary: checked.import_summary,
      projection_exclusions: checked.projection_exclusions,
      exclusion_ledger: checked.exclusion_ledger,
      limitations: [
        ...checked.limitations,
        "Synthetic filtered release records only; not real indicators or completion of issue #20.",
        "Checksums establish byte integrity, not authenticity, completeness or truth. Manifest is unsigned; verify preview pin against trusted repository history.",
      ],
      limits: {
        max_combined_utf8_bytes: MAX_EXPORT_BYTES,
        max_release_records: 100,
      },
    }) + "\n";
  enforceExportLimit(csv, json, manifest);
  return { csv, json, manifest };
}
