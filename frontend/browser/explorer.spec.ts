import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("keyboard navigation, filters, provenance and automated accessibility", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("table")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to research records" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await page.getByLabel("Bid-count availability").selectOption("missing");
  await expect(page.getByRole("status")).toHaveText(
    "1 of 5 synthetic records shown.",
  );
  await expect(page.getByText("Unknown — not supplied")).toBeVisible();
  await page
    .getByLabel("Search identifiers or source reference")
    .fill("unmatched");
  await expect(page.getByText("No records match these filters")).toBeVisible();
  await page.getByRole("button", { name: "Reset filters" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "5 of 5 synthetic records shown.",
  );
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "/tmp/civictrace-explorer-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.screenshot({
    path: "/tmp/civictrace-explorer-desktop.png",
    fullPage: true,
  });
});
test("HTTP failure and delayed load are explicit and retryable", async ({
  page,
}) => {
  await page.route("**/data/synthetic-v1.json", (route) =>
    route.fulfill({ status: 500, body: "unavailable" }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute("**/data/synthetic-v1.json");
  let release: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/data/synthetic-v1.json", async (route) => {
    await gate;
    await route.continue();
  });
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Loading local synthetic records…",
  );
  release?.();
  await expect(page.getByRole("table")).toBeVisible();
});
