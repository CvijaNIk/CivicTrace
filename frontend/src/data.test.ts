import { describe, expect, it, vi } from "vitest";
import { filterRecords, loadDataset, MAX_BYTES, parseDataset } from "./data";
import fixture from "../public/data/synthetic-v1.json";
const valid = () => structuredClone(fixture);
describe("bounded synthetic contract", () => {
  it("preserves five records, unknown and zero distinctly", () => {
    const data = parseDataset(JSON.stringify(valid()));
    expect(data.records).toHaveLength(5);
    expect(data.records[2]?.bid_count).toBeNull();
    expect(data.records[3]?.bid_count).toBe(0);
    expect(filterRecords(data.records, " syn-supplier-1 ", "all")).toHaveLength(
      3,
    );
    expect(
      filterRecords(data.records, "", "missing").map((r) => r.record_id),
    ).toEqual(["SYN-003"]);
    expect(filterRecords(data.records, "none", "all")).toEqual([]);
  });
  it.each([
    (d: ReturnType<typeof valid>) => {
      d.analytics_enabled = true;
    },
    (d: ReturnType<typeof valid>) => {
      d.synthetic = false;
    },
    (d: ReturnType<typeof valid>) => {
      d.schema_version = "unknown";
    },
    (d: ReturnType<typeof valid>) => {
      d.records.push(d.records[0]!);
    },
    (d: ReturnType<typeof valid>) => {
      d.records[0]!.bid_count = -1;
    },
    (d: ReturnType<typeof valid>) => {
      d.records[0]!.bid_count = 0.5;
    },
    (d: ReturnType<typeof valid>) => {
      d.records[0]!.bid_count = Number.MAX_SAFE_INTEGER + 1;
    },
    (d: ReturnType<typeof valid>) => {
      d.records[2]!.data_status = "reported";
    },
    (d: ReturnType<typeof valid>) => {
      d.source.sha256 = "unverified";
    },
    (d: ReturnType<typeof valid>) => {
      d.records[0]!.source_reference = "https://untrusted.example";
    },
    (d: ReturnType<typeof valid>) => {
      d.limitations = [];
    },
    (d: ReturnType<typeof valid>) => {
      d.records = Array(101).fill(d.records[0]);
    },
  ])("rejects invalid metadata, identities, counts and limits", (mutate) => {
    const data = valid();
    mutate(data);
    expect(() => parseDataset(JSON.stringify(data))).toThrow();
  });
  it("accepts a valid empty dataset and enforces encoded byte limit", () => {
    const data = valid();
    data.records = [];
    const raw = JSON.stringify(data);
    expect(parseDataset(raw).records).toEqual([]);
    expect(() =>
      parseDataset(raw + " ".repeat(MAX_BYTES - raw.length)),
    ).not.toThrow();
    expect(() =>
      parseDataset(raw + " ".repeat(MAX_BYTES - raw.length + 1)),
    ).toThrow();
    expect(() => parseDataset("é".repeat(MAX_BYTES / 2 + 1))).toThrow(/limit/);
    expect(() => parseDataset("{")).toThrow();
    expect(() => parseDataset("null")).toThrow();
  });
  it("fails HTTP errors and bounded streaming overflow", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    await expect(loadDataset(new AbortController().signal)).rejects.toThrow(
      /loaded/,
    );
    const cancel = vi.fn();
    const releaseLock = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: {
          getReader: () => ({
            read: vi.fn().mockResolvedValue({
              done: false,
              value: new Uint8Array(MAX_BYTES + 1),
            }),
            cancel,
            releaseLock,
          }),
        },
      }),
    );
    await expect(loadDataset(new AbortController().signal)).rejects.toThrow(
      /limit/,
    );
    expect(cancel).toHaveBeenCalledOnce();
    expect(releaseLock).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
});
