import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("finding compatibility, keyboard, persistent limitations and narrow viewport", async ({
  page,
}) => {
  await page.goto("/?view=passport");
  await expect(page.getByRole("article")).toHaveCount(4);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByText(/Migrated legacy metadata is incomplete/),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Evidence limitations", exact: true }),
  ).toHaveCount(4);
  await expect(page.locator("details,[hidden]")).toHaveCount(0);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to findings" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
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
