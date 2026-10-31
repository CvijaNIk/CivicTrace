import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("verified Parquet preview retains exact values and keyboard filters", async ({
  page,
}) => {
  await page.goto("/?view=parquet");
  await expect(page.getByRole("status")).toHaveText(
    "4 of 4 synthetic procedures shown.",
  );
  await expect(
    page.getByText("9007199254740993.010000000000000000", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("0.000000000000000000", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/amount_outside_decimal256/)).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByText("Skip to snapshot records")).toBeFocused();
  await page.getByLabel("Procedure status").selectOption("cancelled");
  await expect(page.getByRole("status")).toHaveText(
    "1 of 4 synthetic procedures shown.",
  );
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
test("tampered static data fails integrity and recovers on retry", async ({
  page,
}) => {
  await page.route("**/data/parquet-v1.json", async (route) => {
    const response = await route.fetch();
    await route.fulfill({
      response,
      body: (await response.text()).replace(
        "9007199254740993.01",
        "9007199254740994.01",
      ),
    });
  });
  await page.goto("/?view=parquet");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
  await page.unroute("**/data/parquet-v1.json");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "4 of 4 synthetic procedures shown.",
  );
});
