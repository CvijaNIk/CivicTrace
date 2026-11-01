import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { createHash, webcrypto } from "node:crypto";
import { SubmissionPeriodView } from "./SubmissionPeriodView";
import { loadSubmission, verifySubmission } from "./submission";
import fixture from "../public/data/submission-period-v1.json";
import pin from "./submission-pin.json";
const raw = readFileSync("public/data/submission-period-v1.json", "utf8");
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
it("admits exact reviewed bytes with independently verified hash; repeatable", async () => {
  vi.stubGlobal("crypto", webcrypto);
  expect(createHash("sha256").update(raw).digest("hex")).toBe(pin.sha256);
  expect(await verifySubmission(raw)).toEqual(fixture);
  expect(await verifySubmission(raw)).toEqual(await verifySubmission(raw));
});
it.each([
  raw + " ",
  raw.replace('"analytics_enabled": false', '"analytics_enabled": true'),
  raw.replace('"synthetic": true', '"synthetic": false'),
  raw.replace("SYN-OPEN-24", "<img src=x onerror=alert(1)>"),
  raw.replace('"deviation_hours": "-23"', '"deviation_hours": "0"'),
  '{"results":[]}',
  "x".repeat(65537),
])(
  "rejects changed, unsafe, oversized or alternate inputs before display %#",
  async (changed) => {
    vi.stubGlobal("crypto", webcrypto);
    await expect(verifySubmission(changed)).rejects.toThrow();
  },
);
it("renders Python values, explicit unknowns, separate facts/assumptions/results and denominators", async () => {
  render(<SubmissionPeriodView loader={async () => fixture} />);
  await screen.findByRole("heading", { name: "Record details" });
  expect(screen.getAllByRole("article")).toHaveLength(10);
  const offset = within(screen.getAllByRole("article")[0]!);
  expect(offset.getByText("-23")).toBeTruthy();
  expect(offset.getByText("1")).toBeTruthy();
  expect(offset.getByText(fixture.results[0]!.calendar_days!)).toBeTruthy();
  expect(
    offset.getByText(fixture.results[0]!.original_dates.tender_start!),
  ).toBeTruthy();
  expect(offset.getByRole("region", { name: "Source facts" })).toBeTruthy();
  expect(
    offset.getByRole("region", { name: "Synthetic assumptions" }),
  ).toBeTruthy();
  expect(
    offset.getByRole("region", { name: "Computed comparison" }),
  ).toBeTruthy();
  const equal = within(screen.getAllByRole("article")[1]!);
  expect(equal.getAllByText("0").length).toBeGreaterThan(0);
  expect(equal.getByText("-24")).toBeTruthy();
  expect(screen.getByText(/below 3, equal 1, above 0/)).toBeTruthy();
  expect(screen.getByText(/Calendar days are elapsed 24-hour/)).toBeTruthy();
  expect(screen.getAllByText("Unknown — not computed").length).toBeGreaterThan(
    0,
  );
  expect(screen.getAllByText("Not compared")).toHaveLength(6);
  expect(screen.getByText("period_reversed: 1")).toBeTruthy();
  expect(screen.getByText(/no legal or corruption finding/)).toBeTruthy();
  expect(screen.getByText(fixture.input_sha256)).toBeTruthy();
  expect(screen.getByText(fixture.configuration_sha256)).toBeTruthy();
  expect(
    document.querySelector("main img, main iframe, main script"),
  ).toBeNull();
});
it("fails closed on changed HTTP bytes and retries through the real bounded loader", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(new Response(raw + " "))
    .mockResolvedValue(new Response(raw));
  vi.stubGlobal("fetch", fetcher);
  render(<SubmissionPeriodView />);
  await screen.findByRole("alert");
  expect(screen.queryAllByRole("article")).toHaveLength(0);
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByRole("heading", { name: "Record details" });
  expect(fetcher.mock.calls[0]?.[0]).toBe("/data/submission-period-v1.json");
});
it("supports keyboard skip link, navigation and cancels stale completion", async () => {
  let resolve!: (d: typeof fixture) => void;
  const loader = vi.fn((signal: AbortSignal) => {
    expect(signal.aborted).toBe(false);
    return new Promise<typeof fixture>((r) => {
      resolve = r;
    });
  });
  const { unmount } = render(<SubmissionPeriodView loader={loader} />);
  expect(screen.getByRole("status").textContent).toContain("Verifying");
  const user = userEvent.setup();
  await user.tab();
  expect(document.activeElement?.textContent).toBe(
    "Skip to submission periods",
  );
  unmount();
  expect(loader.mock.calls[0]?.[0].aborted).toBe(true);
  resolve(fixture);
});
it("times out without showing results", async () => {
  vi.useFakeTimers();
  const { act } = await import("@testing-library/react");
  render(<SubmissionPeriodView loader={() => new Promise(() => {})} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  expect(screen.getByRole("alert").textContent).toContain(
    "No results displayed",
  );
});
it("uses bounded transport and rejects HTTP errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("failure", { status: 500 })),
  );
  await expect(loadSubmission(new AbortController().signal)).rejects.toThrow();
});
