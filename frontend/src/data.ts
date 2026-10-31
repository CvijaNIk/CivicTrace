export const MAX_BYTES = 65536;
export const MAX_RECORDS = 100;
export interface RecordRow {
  record_id: string;
  buyer_id: string;
  supplier_id: string;
  source_reference: string;
  bid_count: number | null;
  data_status: "missing" | "reported";
}
export interface Dataset {
  schema_version: "civictrace-explorer/1";
  synthetic: true;
  analytics_enabled: false;
  source: {
    name: string;
    path: string;
    sha256: string;
    license: string;
    attribution: string;
    privacy_review: string;
  };
  limitations: string[];
  records: RecordRow[];
}
const object = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && !Array.isArray(x);
const text = (x: unknown): x is string =>
  typeof x === "string" && x.length > 0 && x.length <= 512;
export function parseDataset(raw: string): Dataset {
  if (new TextEncoder().encode(raw).length > MAX_BYTES)
    throw Error("Data exceeds the 64 KiB preview limit.");
  const value: unknown = JSON.parse(raw);
  if (
    !object(value) ||
    value.schema_version !== "civictrace-explorer/1" ||
    value.synthetic !== true ||
    value.analytics_enabled !== false
  )
    throw Error(
      "Only synthetic explorer v1 data with analytics disabled is supported.",
    );
  const source = value.source;
  if (
    !object(source) ||
    ![
      "name",
      "path",
      "sha256",
      "license",
      "attribution",
      "privacy_review",
    ].every((k) => text(source[k])) ||
    !/^[a-f0-9]{64}$/.test(String(source.sha256)) ||
    source.path !== "examples/synthetic_procurement.json" ||
    source.license !== "Apache-2.0"
  )
    throw Error("Invalid source metadata.");
  if (
    !Array.isArray(value.limitations) ||
    value.limitations.length < 1 ||
    value.limitations.length > 10 ||
    !value.limitations.every(text)
  )
    throw Error("Missing or invalid limitations.");
  if (!Array.isArray(value.records) || value.records.length > MAX_RECORDS)
    throw Error("Invalid or oversized record list.");
  const seen = new Set<string>();
  for (const row of value.records) {
    if (
      !object(row) ||
      !["record_id", "buyer_id", "supplier_id", "source_reference"].every((k) =>
        text(row[k]),
      ) ||
      typeof row.record_id !== "string" ||
      !/^SYN-\d{3}$/.test(row.record_id) ||
      !String(row.buyer_id).startsWith("SYN-") ||
      !String(row.supplier_id).startsWith("SYN-") ||
      row.source_reference !== `synthetic:${row.record_id}` ||
      seen.has(row.record_id)
    )
      throw Error("Invalid or duplicate synthetic identity.");
    if (
      row.bid_count !== null &&
      (typeof row.bid_count !== "number" ||
        !Number.isSafeInteger(row.bid_count) ||
        row.bid_count < 0)
    )
      throw Error("Invalid bid count.");
    if (row.data_status !== (row.bid_count === null ? "missing" : "reported"))
      throw Error("Inconsistent data status.");
    seen.add(row.record_id);
  }
  return value as unknown as Dataset;
}
export async function loadDataset(signal: AbortSignal): Promise<Dataset> {
  return loadBounded("data/synthetic-v1.json", parseDataset, signal);
}
export async function loadBounded<T>(
  path: string,
  parse: (raw: string) => T | Promise<T>,
  signal: AbortSignal,
): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}${path}`, {
    signal,
    credentials: "omit",
    redirect: "error",
  });
  if (!response.ok)
    throw Error("The local synthetic data could not be loaded.");
  if (!response.body) throw Error("The local data response is empty.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let raw = "",
    bytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_BYTES)
        throw Error("Data exceeds the 64 KiB preview limit.");
      raw += decoder.decode(value, { stream: true });
    }
    raw += decoder.decode();
    return await parse(raw);
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}
export function filterRecords(
  rows: RecordRow[],
  query: string,
  status: string,
): RecordRow[] {
  const needle = query.trim().toLowerCase();
  return rows.filter(
    (row) =>
      (status === "all" || row.data_status === status) &&
      [row.record_id, row.buyer_id, row.supplier_id, row.source_reference].some(
        (v) => v.toLowerCase().includes(needle),
      ),
  );
}
