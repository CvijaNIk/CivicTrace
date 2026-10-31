import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import fixture from "../public/data/parquet-v1.json";
import { parseParquet, emptyEntityFilters } from "./parquet";
import { FilteredExport } from "./FilteredExport";
import { buildExport } from "./exports";
vi.mock("./exports", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./exports")>()),
  buildExport: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const props = () => ({
  data: parseParquet(JSON.stringify(fixture)),
  filters: { query: "", status: "all", entities: emptyEntityFilters },
  ids: [],
});
it("revokes all generated object URLs when selection is replaced", async () => {
  vi.mocked(buildExport).mockResolvedValue({
    json: "{}",
    csv: "headers",
    manifest: "{}",
  });
  const create = vi
    .fn()
    .mockReturnValueOnce("blob:json")
    .mockReturnValueOnce("blob:csv")
    .mockReturnValueOnce("blob:manifest");
  const revoke = vi.fn();
  vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: revoke });
  const view = render(<FilteredExport {...props()} />);
  await screen.findByRole("link", { name: "Download filtered results.csv" });
  expect(create).toHaveBeenCalledTimes(3);
  view.unmount();
  expect(revoke.mock.calls.flat()).toEqual([
    "blob:json",
    "blob:csv",
    "blob:manifest",
  ]);
  vi.unstubAllGlobals();
});
it("does not publish a pending stale selection after unmount", async () => {
  let finish!: (x: Awaited<ReturnType<typeof buildExport>>) => void;
  vi.mocked(buildExport).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const create = vi.fn();
  vi.stubGlobal("URL", { createObjectURL: create, revokeObjectURL: vi.fn() });
  const view = render(<FilteredExport {...props()} />);
  view.unmount();
  finish({ json: "{}", csv: "headers", manifest: "{}" });
  await waitFor(() => expect(create).not.toHaveBeenCalled());
  vi.unstubAllGlobals();
});
it("shows an accessible failure and no download after rejected consistency/limit check", async () => {
  vi.mocked(buildExport).mockRejectedValue(Error("limit"));
  render(<FilteredExport {...props()} />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Export unavailable",
  );
  expect(screen.queryAllByRole("link")).toHaveLength(0);
});
