import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { PassportFinding } from "./PassportFinding";
import { safeSourceUrl, validatePassport } from "./passport";
import example from "./passport-example.json";
afterEach(cleanup);
const legacy = (): any => structuredClone(example.findings[0]!);
const complete = (): any => structuredClone(example.findings[2]!);
describe("synthetic finding contracts", () => {
  it.each(example.findings.map((p, i) => [i, p] as const))(
    "accepts version/migration example %s without mutation",
    (_, p) => {
      const before = JSON.stringify(p);
      expect(validatePassport(p)).toEqual(p);
      expect(JSON.stringify(p)).toBe(before);
    },
  );
  it("preserves unknowns, zero, exact decimals, and deterministic order", () => {
    const p = legacy();
    p.facts = {
      z: null,
      a: "9007199254740993.010000000000000001",
      count: 0,
    } as typeof p.facts;
    const markup = () =>
      renderToStaticMarkup(<PassportFinding passport={p} synthetic />);
    expect(markup()).toBe(markup());
    render(<PassportFinding passport={p} synthetic />);
    expect(
      screen.getAllByText("Unknown — not supplied").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText("9007199254740993.010000000000000001"),
    ).toBeTruthy();
    expect(screen.getByText("0")).toBeTruthy();
  });
  it.each([
    "source",
    "rule",
    "limitations",
    "schema_version",
    "computation",
    "verification_steps",
  ])("rejects missing %s", (key) => {
    const p = legacy() as Record<string, unknown>;
    delete p[key];
    expect(() => validatePassport(p)).toThrow();
  });
  it.each([
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "//evil.example",
    "https://a.example\\@evil.example",
    "https://user:pass@example.com",
    " https://example.com",
    "https://exa\nmple.com",
    "urn:synthetic:source",
    "https://",
  ])("keeps unsafe or local reference inert: %s", (reference) => {
    const p = legacy();
    p.source.reference = reference;
    render(<PassportFinding passport={p} synthetic />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(safeSourceUrl(reference)).toBeNull();
  });
  it("renders HTML/JS as inert text in every free-text group", () => {
    const p = legacy();
    const attack = '<img src=x onerror="alert(1)"><script>alert(2)</script>';
    p.source.name = attack;
    p.facts = { buyer_id: attack, supplier_id: attack };
    p.interpretation = attack;
    p.limitations = [attack];
    p.allegations = [attack];
    p.verification_steps = [attack];
    const { container } = render(<PassportFinding passport={p} synthetic />);
    expect(container.querySelector("img,script,iframe,svg")).toBeNull();
    expect(screen.getAllByText(attack).length).toBeGreaterThan(4);
    expect(
      screen.getByRole("heading", { name: /Unverified allegations/ }),
    ).toBeTruthy();
  });
  it("permits only explicit HTTP(S) anchors without credentials or referrer", () => {
    const p = legacy();
    p.source.reference = "https://example.invalid/synthetic?q=1";
    render(<PassportFinding passport={p} synthetic />);
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe(p.source.reference);
    expect(link.getAttribute("referrerpolicy")).toBe("no-referrer");
  });
  it("keeps long limitations open and uses unique internal headings", () => {
    const p = legacy();
    p.limitations = ["long ".repeat(2000) + "END OF LIMITATION"];
    const { container } = render(
      <>
        <PassportFinding passport={p} synthetic />
        <PassportFinding passport={p} synthetic />
      </>,
    );
    expect(container.querySelector("details,[hidden]")).toBeNull();
    expect(container.textContent?.match(/END OF LIMITATION/g)?.length).toBe(2);
    const ids = [...container.querySelectorAll("[id]")].map((n) => n.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it("rejects non synthetic usage, unsupported versions, invalid sources and unsafe numbers", () => {
    render(<PassportFinding passport={legacy()} synthetic={false} />);
    expect(screen.getByRole("alert")).toBeTruthy();
    for (const mutate of [
      (p: any) => (p.schema_version = "9"),
      (p: any) => (p.source = null),
      (p: any) => (p.source.original_file_sha256 = "wrong"),
      (p: any) => (p.source.collected_at = "yesterday"),
      (p: any) => (p.facts.amount = 9007199254740992),
    ]) {
      const p = legacy();
      mutate(p);
      expect(() => validatePassport(p)).toThrow();
    }
  });
  it("fails closed on conflicting, missing and broken lineage", () => {
    for (const mutate of [
      (p: any) => delete p.lineage.environment,
      (p: any) => (p.lineage.decompressed_sha256 = null),
      (p: any) => (p.lineage.analytics_enabled = true),
      (p: any) => (p.lineage.original_file_sha256 = "a".repeat(64)),
      (p: any) => p.lineage.artifacts.push(p.lineage.artifacts[0]),
      (p: any) => (p.lineage.transformations[0].inputs = ["missing"]),
    ]) {
      const p = complete();
      mutate(p);
      expect(() => validatePassport(p)).toThrow();
    }
  });
  it("rejects oversized/deep content without truncating evidence", () => {
    const p = legacy();
    p.limitations = ["x".repeat(16385)];
    expect(() => validatePassport(p)).toThrow();
    let deep: any = null;
    for (let i = 0; i < 18; i++) deep = { next: deep };
    p.facts = deep;
    expect(() => validatePassport(p)).toThrow();
  });
});
