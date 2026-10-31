import { loadBounded, MAX_BYTES, MAX_RECORDS } from "./data";
import pin from "./parquet-pin.json";
type Obj = Record<string, unknown>;
const obj = (x: unknown): x is Obj =>
  typeof x === "object" && x !== null && !Array.isArray(x);
const text = (x: unknown): x is string =>
  typeof x === "string" && x.length > 0 && x.length <= 4096;
const hash = (x: unknown): x is string =>
  typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
export interface Field {
  state: string;
  value: string | null;
}
export interface Entity {
  amount: string | null;
  projection_exclusion: string | null;
  record_sha256: string;
  source_file: string;
  canonical: {
    id: string;
    process_id: string;
    release_id: string;
    source_id: string;
    date: Field;
    status: Field;
    source_record?: { ocid: string };
    money?: { amount: Field; currency: Field };
  };
}
export interface SearchEntity {
  source_id: Field;
  name: Field;
  pointer: string;
  pointer_scope:
    "release_source_record" | "party_canonical" | "contract_canonical";
  canonical_id: string | null;
  source_file: string;
  record_sha256: string;
}
export type EntityFilters = Record<
  | "buyerId"
  | "buyerName"
  | "supplierId"
  | "supplierName"
  | "contractId"
  | "contractName",
  string
>;
export const emptyEntityFilters: EntityFilters = {
  buyerId: "",
  buyerName: "",
  supplierId: "",
  supplierName: "",
  contractId: "",
  contractName: "",
};
export interface ParquetData {
  schema_version: string;
  snapshot_id: string;
  snapshot_version: string;
  canonical_schema_version: string;
  analytics_enabled: false;
  synthetic: true;
  records: {
    release: Entity;
    awards: Entity[];
    contracts: Entity[];
    search: Record<"buyers" | "suppliers" | "contracts", SearchEntity[]>;
  }[];
  lineage: {
    snapshot_id: string;
    original_file_sha256: string;
    decompressed_sha256: string;
    source: Record<string, unknown>;
    artifacts: unknown[];
  };
  import_summary: { accepted: number; rejected: number; rows: number };
  projection_exclusions: number;
  exclusion_ledger: unknown[];
  limitations: string[];
}
export function matchesEntities(
  row: ParquetData["records"][number],
  filters: EntityFilters,
): boolean {
  return (
    [
      ["buyers", "buyerId", "buyerName"],
      ["suppliers", "supplierId", "supplierName"],
      ["contracts", "contractId", "contractName"],
    ] as const
  ).every(([kind, idKey, nameKey]) => {
    const id = filters[idKey];
    const name = filters[nameKey].trim().toLowerCase();
    return (
      (!id && !name) ||
      row.search[kind].some(
        (entity) =>
          (!id ||
            (entity.source_id.state === "present" &&
              entity.source_id.value === id)) &&
          (!name ||
            (entity.name.state === "present" &&
              entity.name.value!.toLowerCase().includes(name))),
      )
    );
  });
}
function searchEntity(x: unknown): x is SearchEntity {
  return (
    obj(x) &&
    field(x.source_id) &&
    field(x.name) &&
    text(x.pointer) &&
    ["release_source_record", "party_canonical", "contract_canonical"].includes(
      String(x.pointer_scope),
    ) &&
    (x.canonical_id === null || hash(x.canonical_id)) &&
    text(x.source_file) &&
    hash(x.record_sha256)
  );
}
function field(x: unknown): x is Field {
  return (
    obj(x) &&
    ["present", "absent", "null", "invalid", "unsupported"].includes(
      String(x.state),
    ) &&
    (x.state === "present" ? text(x.value) : x.value === null)
  );
}
function entity(x: unknown): x is Entity {
  if (
    !obj(x) ||
    !hash(x.record_sha256) ||
    !text(x.source_file) ||
    (x.amount !== null &&
      (typeof x.amount !== "string" ||
        !/^-?\d{1,58}\.\d{18}$/.test(x.amount))) ||
    (x.projection_exclusion !== null &&
      x.projection_exclusion !== "amount_outside_decimal256_76_18") ||
    (x.projection_exclusion !== null && x.amount !== null) ||
    !obj(x.canonical)
  )
    return false;
  const c = x.canonical;
  if (
    ![c.id, c.process_id, c.release_id].every(hash) ||
    !text(c.source_id) ||
    !field(c.date) ||
    !field(c.status)
  )
    return false;
  if (c.money !== undefined) {
    if (!obj(c.money) || !field(c.money.amount) || !field(c.money.currency))
      return false;
    if (c.money.amount.state !== "present" && x.amount !== null) return false;
  }
  return true;
}
export function parseParquet(raw: string): ParquetData {
  if (new TextEncoder().encode(raw).length > MAX_BYTES)
    throw Error("Preview byte limit");
  const x: unknown = JSON.parse(raw);
  if (
    !obj(x) ||
    x.schema_version !== "civictrace-parquet-explorer/2" ||
    x.synthetic !== true ||
    x.analytics_enabled !== false ||
    x.snapshot_id !== pin.snapshot_id ||
    x.snapshot_version !== "civictrace-parquet/1" ||
    !text(x.canonical_schema_version) ||
    !obj(x.lineage) ||
    x.lineage.snapshot_id !== x.snapshot_id ||
    !hash(x.lineage.original_file_sha256) ||
    !hash(x.lineage.decompressed_sha256) ||
    !obj(x.lineage.source) ||
    !Array.isArray(x.lineage.artifacts) ||
    !obj(x.import_summary) ||
    ![
      x.import_summary.accepted,
      x.import_summary.rejected,
      x.import_summary.rows,
    ].every(
      (v) => typeof v === "number" && Number.isSafeInteger(v) && v >= 0,
    ) ||
    Number(x.import_summary.accepted) + Number(x.import_summary.rejected) !==
      x.import_summary.rows ||
    !Array.isArray(x.limitations) ||
    x.limitations.length < 1 ||
    x.limitations.length > 10 ||
    !x.limitations.every(text) ||
    !Array.isArray(x.exclusion_ledger) ||
    x.exclusion_ledger.length !== x.import_summary.rows ||
    typeof x.projection_exclusions !== "number" ||
    !Number.isSafeInteger(x.projection_exclusions) ||
    x.projection_exclusions < 0 ||
    !Array.isArray(x.records) ||
    x.records.length > MAX_RECORDS ||
    x.records.length !== x.import_summary.accepted
  )
    throw Error("Unsupported preview metadata");
  const seen = new Set<string>();
  for (const r of x.records) {
    if (
      !obj(r) ||
      !entity(r.release) ||
      !obj(r.release.canonical.source_record) ||
      !text(r.release.canonical.source_record.ocid) ||
      seen.has(r.release.canonical.id)
    )
      throw Error("Invalid release");
    const release = r.release;
    if (!obj(r.search)) throw Error("Missing search projection");
    for (const kind of ["buyers", "suppliers", "contracts"] as const) {
      const items = r.search[kind];
      if (
        !Array.isArray(items) ||
        items.length > 1000 ||
        !items.every(searchEntity)
      )
        throw Error("Invalid search projection");
      if (
        items.some(
          (item) =>
            item.source_file !== release.source_file ||
            item.record_sha256 !== release.record_sha256,
        )
      )
        throw Error("Search evidence mismatch");
      if (
        kind === "contracts" &&
        (items.length !== (r.contracts as unknown[]).length ||
          items.some(
            (item) =>
              !(r.contracts as Entity[]).some(
                (c) =>
                  c.canonical.id === item.canonical_id &&
                  c.canonical.source_id === item.source_id.value,
              ),
          ))
      )
        throw Error("Search contract mismatch");
    }
    seen.add(r.release.canonical.id);
    for (const table of [r.awards, r.contracts]) {
      if (!Array.isArray(table) || table.length > 1000)
        throw Error("Child limit");
      const children = new Set<string>();
      for (const c of table) {
        if (
          !entity(c) ||
          !c.canonical.money ||
          c.canonical.release_id !== r.release.canonical.id ||
          c.canonical.process_id !== r.release.canonical.process_id ||
          children.has(c.canonical.id)
        )
          throw Error("Invalid child");
        children.add(c.canonical.id);
      }
    }
  }
  return x as unknown as ParquetData;
}
export async function loadParquet(signal: AbortSignal): Promise<ParquetData> {
  return loadBounded(
    "data/parquet-v1.json",
    async (raw) => {
      const digest = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(raw),
      );
      const hex = Array.from(new Uint8Array(digest), (b) =>
        b.toString(16).padStart(2, "0"),
      ).join("");
      if (hex !== pin.sha256) throw Error("Preview checksum mismatch");
      return parseParquet(raw);
    },
    signal,
  );
}
