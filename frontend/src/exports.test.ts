import { expect, it, vi } from "vitest";
import { webcrypto, createHash } from "node:crypto";
import fixture from "../public/data/parquet-v1.json";
import { parseParquet, emptyEntityFilters } from "./parquet";
import {
  buildExport,
  canonicalJSON,
  csvCell,
  selectRecords,
  MAX_EXPORT_BYTES,
  enforceExportLimit,
  type ExportFilters,
} from "./exports";
vi.stubGlobal("crypto", webcrypto);
const data = () => parseParquet(JSON.stringify(fixture));
const filters = (entities = {}, query = "", status = "all"): ExportFilters => ({
  query,
  status,
  entities: { ...emptyEntityFilters, ...entities },
});
const run = (f = filters(), d = data()) =>
  buildExport(
    d,
    f,
    selectRecords(d, f).map((r) => r.release.canonical.id),
  );
// Independent RFC4180 reader: handles quoted commas, CRLF and escaped quotes.
function readCSV(s: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === '"') {
      if (quoted && s[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (!quoted && c === ",") {
      row.push(cell);
      cell = "";
    } else if (!quoted && c === "\r" && s[i + 1] === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
      i++;
    } else cell += c;
  }
  return rows;
}
it("exports exactly the combined source/status/entity selection, including same-name distinct IDs", async () => {
  const names = JSON.parse(
    (await run(filters({ buyerName: "Invented Council" }))).json,
  );
  expect(names.records).toHaveLength(3);
  expect(
    new Set(
      names.records.map(
        (r: (typeof fixture.records)[number]) =>
          r.search.buyers[0]!.source_id.value,
      ),
    ).size,
  ).toBe(3);
  const f = filters({
    buyerName: "INVENTED COUNCIL",
    supplierId: "SYN-SUPPLIER-0",
    contractId: "SYN-CONTRACT-0",
  });
  const selected = selectRecords(data(), f);
  expect(selected).toHaveLength(1);
  f.query = selected[0]!.release.canonical.source_id;
  f.status = selected[0]!.release.canonical.status.value!;
  const out = await run(f);
  expect(JSON.parse(out.json).records).toEqual(selected);
  expect(JSON.parse(out.manifest).filters).toEqual(f);
  expect(
    JSON.parse(
      (
        await run(
          filters({ buyerId: "SYN-BUYER-0", supplierId: "SYN-SUPPLIER-1" }),
        )
      ).json,
    ).records,
  ).toEqual([]);
});
it("empty exports have headers, explicit zero count and valid checksums", async () => {
  const out = await run(filters({}, "no-such-source"));
  expect(readCSV(out.csv)).toHaveLength(1);
  expect(JSON.parse(out.json).records).toEqual([]);
  expect(JSON.parse(out.manifest).result_count).toBe(0);
});
it("round trips CSV/JSON source IDs, nested evidence, null/states, exact amounts and exclusions", async () => {
  const out = await run();
  const records = JSON.parse(out.json).records;
  const csv = readCSV(out.csv)
    .slice(1)
    .map((row) => row.map((s) => JSON.parse(s)));
  expect(
    csv.map((r) => ({
      release: r[5],
      search: r[6],
      awards: r[7],
      contracts: r[8],
    })),
  ).toEqual(records);
  expect(records).toEqual(data().records);
  expect(out.json).toContain("9007199254740993.010000000000000000");
  expect(out.json).toContain("0.000000000000000000");
  expect(out.json).toContain('"state":"absent","value":null');
  expect(out.json).toContain("amount_outside_decimal256_76_18");
  const m = JSON.parse(out.manifest);
  expect(m.lineage).toEqual(data().lineage);
  expect(m.exclusion_ledger).toEqual(data().exclusion_ledger);
  expect(m.analytics_enabled).toBe(false);
  for (const [name, text] of [
    ["results.json", out.json],
    ["results.csv", out.csv],
  ]) {
    expect(m.files[name!].sha256).toBe(
      createHash("sha256").update(text!).digest("hex"),
    );
    expect(m.files[name!].bytes).toBe(new TextEncoder().encode(text!).length);
  }
  expect(
    Object.values(out).reduce(
      (n, s) => n + new TextEncoder().encode(s).length,
      0,
    ),
  ).toBeLessThanOrEqual(MAX_EXPORT_BYTES);
});
it.each([
  "=1+1",
  "+SUM(A1)",
  "-1+1",
  "@SUM(A1)",
  "\t=1",
  "\r=1",
  "\n+1",
  " \t@x",
  "\uFEFF=1",
  "\u200B=1",
  "＝1",
  'a,"b"\r\nc',
  "0012",
  "9007199254740993.01",
])("neutralizes spreadsheet text prefixes and round trips %j", (s) => {
  const decoded = readCSV(csvCell(s) + "\r\n")[0]![0]!;
  expect(decoded[0]).toBe('"'); // Spreadsheet sees literal JSON quote, never a formula prefix.
  expect(JSON.parse(decoded)).toBe(s);
});
it("deterministic bytes despite object-key insertion order and repeated builds", async () => {
  const d = data();
  const f = filters({ buyerName: "Invented Council" });
  const first = await run(f, d);
  const reversed = (x: unknown): unknown =>
    Array.isArray(x)
      ? x.map(reversed)
      : x && typeof x === "object"
        ? Object.fromEntries(
            Object.entries(x)
              .reverse()
              .map(([k, v]) => [k, reversed(v)]),
          )
        : x;
  expect(await run(f, reversed(d) as typeof d)).toEqual(first);
  expect(await run(f, d)).toEqual(first);
  expect(canonicalJSON({ b: 1, a: null })).toBe('{"a":null,"b":1}');
});
it("fails closed for stale display, wrong gates, oversized input/output and invalid filters", async () => {
  await expect(buildExport(data(), filters(), [])).rejects.toThrow("differ");
  const d = data();
  (d as { synthetic: boolean }).synthetic = false;
  await expect(run(filters(), d)).rejects.toThrow();
  await expect(run(filters({}, "x".repeat(129)))).rejects.toThrow("filters");
  const big = data();
  big.limitations = ["x".repeat(65536)];
  await expect(run(filters(), big)).rejects.toThrow();
  expect(() =>
    enforceExportLimit("é".repeat(MAX_EXPORT_BYTES / 2)),
  ).not.toThrow();
  expect(() =>
    enforceExportLimit("é".repeat(MAX_EXPORT_BYTES / 2), "x"),
  ).toThrow("byte limit");
  expect(() =>
    enforceExportLimit("x".repeat(MAX_EXPORT_BYTES - 2), "x", "xx"),
  ).toThrow("byte limit");
});
