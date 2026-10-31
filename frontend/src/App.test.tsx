import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { parseDataset } from "./data";
import fixture from "../public/data/synthetic-v1.json";
afterEach(cleanup);
const data = parseDataset(JSON.stringify(fixture));
it("announces loading and renders keyboard-operable filters, unknown and provenance", async () => {
  const user = userEvent.setup();
  render(<App loader={() => Promise.resolve(data)} />);
  expect(screen.getByRole("status").textContent).toContain("Loading");
  await screen.findByText("5 of 5 synthetic records shown.");
  expect(screen.getByText("Unknown — not supplied")).toBeTruthy();
  expect(screen.getByRole("cell", { name: "0" })).toBeTruthy();
  expect(screen.getByText(data.source.sha256)).toBeTruthy();
  await user.tab();
  expect(document.activeElement?.textContent).toContain("Skip to research");
  await user.type(
    screen.getByLabelText("Search identifiers or source reference"),
    "SYN-003",
  );
  expect(screen.getByRole("status").textContent).toContain("1 of 5");
  await user.selectOptions(
    screen.getByLabelText("Bid-count availability"),
    "reported",
  );
  expect(screen.getByText("No records match these filters")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(screen.getByRole("status").textContent).toContain("5 of 5");
});
it("recovers from an error via retry", async () => {
  const loader = vi
    .fn()
    .mockRejectedValueOnce(Error("failure"))
    .mockResolvedValue(data);
  render(<App loader={loader} />);
  await screen.findByRole("alert");
  expect(screen.queryByRole("table")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByRole("table");
  expect(loader).toHaveBeenCalledTimes(2);
});
it("renders valid empty data and aborts the loader on unmount", async () => {
  let signal: AbortSignal | undefined;
  const view = render(
    <App
      loader={(s) => {
        signal = s;
        return Promise.resolve({ ...data, records: [] });
      }}
    />,
  );
  await screen.findByText("The synthetic dataset contains no records");
  view.unmount();
  expect(signal?.aborted).toBe(true);
});
it("does not render a late response after unmount", async () => {
  let resolve: ((value: typeof data) => void) | undefined;
  const view = render(
    <App
      loader={() =>
        new Promise((r) => {
          resolve = r;
        })
      }
    />,
  );
  view.unmount();
  resolve?.(data);
  await waitFor(() => expect(screen.queryByRole("table")).toBeNull());
});
