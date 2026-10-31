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

test("entity filters retain exact identity, combine, reset and support keyboard/axe", async ({
  page,
}) => {
  await page.goto("/?view=parquet");
  await expect(page.getByRole("status")).toHaveText(
    "4 of 4 synthetic procedures shown.",
  );
  await page.getByLabel("Buyer name contains").focus();
  await page.keyboard.type("Invented Council");
  await expect(page.getByRole("status")).toHaveText(
    "3 of 4 synthetic procedures shown.",
  );
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Supplier / tenderer exact ID")).toBeFocused();
  await page.keyboard.type("SYN-SUPPLIER-1");
  await expect(page.getByRole("status")).toHaveText(
    "1 of 4 synthetic procedures shown.",
  );
  await expect(
    page.getByRole("region", { name: "Active filters" }),
  ).toContainText("SYN-SUPPLIER-1");
  await page.getByLabel("Contract exact ID").fill("SYN-CONTRACT-0");
  await expect(
    page.getByText("No procedures match these filters."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset filters" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status")).toHaveText(
    "4 of 4 synthetic procedures shown.",
  );
  await page.getByLabel("Buyer exact ID").fill("SYN-BUYER-0");
  await expect(page.getByRole("status")).toHaveText(
    "1 of 4 synthetic procedures shown.",
  );
  await page.getByLabel("Buyer exact ID").fill("syn-buyer-0");
  await expect(page.getByRole("status")).toHaveText(
    "0 of 4 synthetic procedures shown.",
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

test("filtered downloads agree with display and manifest; reset and empty results invalidate links", async ({
  page,
}) => {
  const { readFile } = await import("node:fs/promises");
  const { createHash } = await import("node:crypto");
  await page.goto("/?view=parquet");
  await page.getByLabel("Buyer name contains").fill("Invented Council");
  await page.getByLabel("Supplier / tenderer exact ID").fill("SYN-SUPPLIER-0");
  await expect(page.getByRole("status")).toHaveText(
    "1 of 4 synthetic procedures shown.",
  );
  async function download(name: string) {
    const pending = page.waitForEvent("download");
    await page
      .getByRole("link", { name: `Download filtered ${name}`, exact: true })
      .click();
    const file = await pending;
    expect(file.suggestedFilename()).toBe(name);
    return readFile((await file.path())!);
  }
  const json = await download("results.json");
  const csv = await download("results.csv");
  const manifest = JSON.parse((await download("manifest.json")).toString());
  const result = JSON.parse(json.toString());
  expect(result.records).toHaveLength(1);
  expect(result.records[0].search.suppliers[0].source_id.value).toBe(
    "SYN-SUPPLIER-0",
  );
  expect(result.analytics_enabled).toBe(false);
  expect(manifest.record_ids).toEqual(
    result.records.map(
      (r: { release: { canonical: { id: string } } }) => r.release.canonical.id,
    ),
  );
  expect(manifest.filters.entities.supplierId).toBe("SYN-SUPPLIER-0");
  for (const [name, bytes] of [
    ["results.json", json],
    ["results.csv", csv],
  ] as const) {
    expect(manifest.files[name].sha256).toBe(
      createHash("sha256").update(bytes).digest("hex"),
    );
    expect(manifest.files[name].bytes).toBe(bytes.length);
  }
  await expect(
    page.getByRole("link", {
      name: "Download verified synthetic preview JSON",
    }),
  ).toHaveAttribute("href", "data/parquet-v1.json");
  await page.getByLabel("Contract exact ID").fill("no-such-id");
  expect(
    JSON.parse((await download("results.json")).toString()).records,
  ).toEqual([]);
  expect(
    JSON.parse((await download("manifest.json")).toString()).result_count,
  ).toBe(0);
  await page.getByRole("button", { name: "Reset filters" }).click();
  expect(
    JSON.parse((await download("results.json")).toString()).records,
  ).toHaveLength(4);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});
