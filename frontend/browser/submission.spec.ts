import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("controlled submission report, keyboard, unknowns, integrity failure and accessibility", async ({
  page,
}) => {
  await page.goto("/?view=parquet");
  await page.getByRole("link", { name: "Submission periods" }).click();
  await expect(page.getByRole("article")).toHaveCount(10);
  await expect(
    page.getByText("below 3, equal 1, above 0.", { exact: false }),
  ).toBeVisible();
  const first = page.getByRole("article").first();
  await expect(first.getByText("-23", { exact: true })).toBeVisible();
  await expect(
    first.getByText("2026-01-01T23:30:00-03:00", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Unknown — not computed", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("period_reversed: 1", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Invented test references — no legal or corruption finding"),
  ).toBeVisible();
  await page.goto("/?view=submission-period");
  await expect(page.getByRole("article")).toHaveCount(10);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to submission periods" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "/tmp/civictrace-submission-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "/tmp/civictrace-submission-desktop.png",
    fullPage: true,
  });
  await page.route("**/data/submission-period-v1.json", async (route) => {
    const response = await route.fetch();
    await route.fulfill({
      response,
      body: (await response.text()).replace(
        '"analytics_enabled": false',
        '"analytics_enabled": true',
      ),
    });
  });
  await page.reload();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.unroute("**/data/submission-period-v1.json");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("article")).toHaveCount(10);
});
