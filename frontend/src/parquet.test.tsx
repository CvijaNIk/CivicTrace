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
