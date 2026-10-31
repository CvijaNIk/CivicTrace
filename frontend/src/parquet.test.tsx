import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fixture from "../public/data/parquet-v1.json";
import { parseParquet } from "./parquet";
import { ParquetExplorer } from "./ParquetExplorer";
afterEach(cleanup);
const raw = JSON.stringify(fixture);
it("validates exact strings", () =>
  expect(parseParquet(raw).records).toHaveLength(4));
it.each([
  (d: typeof fixture) => {
    d.analytics_enabled = true;
  },
  (d: typeof fixture) => {
    d.snapshot_id = "0".repeat(64);
  },
  (d: typeof fixture) => {
    d.records.push(d.records[0]!);
  },
  (d: typeof fixture) => {
    (d.records[0]!.awards[0]! as unknown as { amount: unknown }).amount =
      9007199254740993;
  },
  (d: typeof fixture) => {
    d.records[0]!.awards[0]!.canonical.release_id = "0".repeat(64);
  },
])(
  "rejects changed gate, identity, duplicate, numeric money and broken relationship",
  (mutate) => {
    const d = structuredClone(fixture);
    mutate(d);
    expect(() => parseParquet(JSON.stringify(d))).toThrow();
  },
);
it("rejects byte limits", () =>
  expect(() => parseParquet(" ".repeat(65537))).toThrow());
it("renders exact values, filters, missing states, provenance and exclusions", async () => {
  const user = userEvent.setup();
  render(<ParquetExplorer loader={() => Promise.resolve(parseParquet(raw))} />);
  await screen.findByText("4 of 4 synthetic procedures shown.");
  expect(screen.getByText("9007199254740993.010000000000000000")).toBeTruthy();
  expect(screen.getByText("0.000000000000000000")).toBeTruthy();
  expect(screen.getAllByText("Unknown — absent").length).toBeGreaterThan(0);
  expect(screen.getByText(/amount_outside_decimal256/)).toBeTruthy();
  expect(screen.getByText(fixture.snapshot_id)).toBeTruthy();
  await user.selectOptions(
    screen.getByLabelText("Procedure status"),
    "cancelled",
  );
  expect(screen.getByRole("status").textContent).toContain("1 of 4");
  await user.type(
    screen.getByLabelText("Search source identifiers"),
    "not-present",
  );
  expect(screen.getByText("No procedures match these filters.")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(screen.getByRole("status").textContent).toContain("4 of 4");
});
it("retries rejected payload and aborts on unmount", async () => {
  const loader = vi
    .fn()
    .mockRejectedValueOnce(Error("integrity"))
    .mockResolvedValue(parseParquet(raw));
  const view = render(<ParquetExplorer loader={loader} />);
  await screen.findByRole("alert");
  expect(screen.queryByRole("table")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("4 of 4 synthetic procedures shown.");
  view.unmount();
  expect((loader.mock.calls[1]![0] as AbortSignal).aborted).toBe(true);
});

import { emptyEntityFilters, matchesEntities } from "./parquet";
it("keeps same-name entities distinct; exact IDs preserve case and whitespace", () => {
  const data = parseParquet(raw);
  const filter = (changes: Partial<typeof emptyEntityFilters>) =>
    data.records.filter((r) =>
      matchesEntities(r, { ...emptyEntityFilters, ...changes }),
    );
  expect(filter({ buyerName: "invented council" })).toHaveLength(3);
  expect(filter({ buyerId: "SYN-BUYER-0" })).toHaveLength(1);
  expect(filter({ buyerId: "SYN-BUYER" })).toHaveLength(0);
  expect(filter({ buyerId: "syn-buyer-0" })).toHaveLength(0);
  expect(filter({ buyerId: " SYN-BUYER-0" })).toHaveLength(0);
  expect(filter({ supplierName: "  INVENTED WORKS  " })).toHaveLength(3);
  expect(filter({ contractName: "maintenance" })).toHaveLength(3);
  expect(
    filter({ buyerId: "SYN-BUYER-0", supplierId: "SYN-SUPPLIER-1" }),
  ).toHaveLength(0);
  expect(
    filter({
      buyerId: "SYN-BUYER-0",
      supplierId: "SYN-SUPPLIER-0",
      contractId: "SYN-CONTRACT-0",
    }),
  ).toHaveLength(1);
  expect(filter({ buyerName: "Unknown" })).toHaveLength(0);
  expect(filter({})).toHaveLength(4);
});
it("requires ID and name on the same party and same contract", () => {
  const row = structuredClone(parseParquet(raw).records[0]!);
  const party = row.search.suppliers[0]!;
  row.search.suppliers = [
    {
      ...party,
      source_id: { state: "present", value: "A" },
      name: { state: "present", value: "Alpha" },
    },
    {
      ...party,
      source_id: { state: "present", value: "B" },
      name: { state: "present", value: "Beta" },
    },
  ];
  expect(
    matchesEntities(row, {
      ...emptyEntityFilters,
      supplierId: "A",
      supplierName: "Beta",
    }),
  ).toBe(false);
  expect(
    matchesEntities(row, {
      ...emptyEntityFilters,
      supplierId: "B",
      supplierName: "Beta",
    }),
  ).toBe(true);
  row.search.contracts = row.search.suppliers;
  expect(
    matchesEntities(row, {
      ...emptyEntityFilters,
      contractId: "A",
      contractName: "Beta",
    }),
  ).toBe(false);
});
it.each(["buyers", "suppliers", "contracts"] as const)(
  "rejects malformed %s and mismatched evidence",
  (kind) => {
    const data = JSON.parse(raw);
    data.records[0].search[kind][0].name = { state: "present", value: null };
    expect(() => parseParquet(JSON.stringify(data))).toThrow();
    data.records[0].search[kind][0].name = { state: "absent", value: null };
    data.records[0].search[kind][0].record_sha256 = "0".repeat(64);
    expect(() => parseParquet(JSON.stringify(data))).toThrow();
  },
);
it("shows active filters, unknown inputs, combined counts and resets using keyboard", async () => {
  const user = userEvent.setup();
  render(<ParquetExplorer loader={() => Promise.resolve(parseParquet(raw))} />);
  await screen.findByText("4 of 4 synthetic procedures shown.");
  const name = screen.getByLabelText("Buyer name contains");
  name.focus();
  await user.keyboard("Invented Council");
  expect(screen.getByRole("status").textContent).toContain("3 of 4");
  expect(
    screen.getByRole("region", { name: "Active filters" }).textContent,
  ).toContain("Invented Council");
  await user.tab();
  expect(document.activeElement).toBe(
    screen.getByLabelText("Supplier / tenderer exact ID"),
  );
  await user.keyboard("SYN-SUPPLIER-1");
  expect(screen.getByRole("status").textContent).toContain("1 of 4");
  await user.selectOptions(
    screen.getByLabelText("Procedure status"),
    "complete",
  );
  expect(screen.getByText("No procedures match these filters.")).toBeTruthy();
  const reset = screen.getByRole("button", { name: "Reset filters" });
  reset.focus();
  await user.keyboard("{Enter}");
  expect(screen.getByRole("status").textContent).toContain("4 of 4");
  expect(screen.getByText("No active filters.")).toBeTruthy();
  await user.type(
    screen.getByLabelText("Search source identifiers"),
    "SYN-000002",
  );
  expect(screen.getByRole("status").textContent).toContain("1 of 4");
  expect(screen.getAllByText(/Unknown — null/).length).toBeGreaterThan(0);
});
