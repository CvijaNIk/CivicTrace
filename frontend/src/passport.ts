import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import legacy from "../../schemas/evidence-passport-0.1.0.schema.json";
import current from "../../schemas/evidence-passport-0.2.0.schema.json";
export type Json =
  null | boolean | number | string | Json[] | { [key: string]: Json };
export type Obj = { [key: string]: Json };
const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
// Separate instances: the historical frozen schemas share an $id.
const validators = [legacy, current].map((schema) => {
  const ajv = new Ajv2020({
    strict: false,
    allErrors: false,
    ownProperties: true,
  });
  addFormats(ajv);
  return ajv.compile(schema);
});
function bounded(v: unknown, depth = 0, budget = { nodes: 0 }): boolean {
  if (++budget.nodes > 10000 || depth > 16) return false;
  if (v === null || typeof v === "boolean") return true;
  if (typeof v === "number") return Number.isSafeInteger(v);
  if (typeof v === "string") return v.length <= 16384;
  if (Array.isArray(v))
    return v.length <= 256 && v.every((x) => bounded(x, depth + 1, budget));
  return (
    object(v) &&
    Object.entries(v).every(
      ([k, x]) => k.length <= 256 && bounded(x, depth + 1, budget),
    )
  );
}
export function validatePassport(v: unknown): Obj {
  if (
    !bounded(v) ||
    !object(v) ||
    !validators[v.schema_version === "0.1.0" ? 0 : 1]!(v)
  )
    throw Error("Unsupported or incomplete Evidence Passport");
  if (v.schema_version === "0.2.0") {
    const l = v.lineage as Obj,
      source = v.source as Obj;
    if (
      l.original_file_sha256 !== source.original_file_sha256 ||
      l.collection_time !== source.collected_at
    )
      throw Error("Conflicting source lineage");
    const ids = (l.artifacts as Obj[]).map((a) => a.id);
    if (new Set(ids).size !== ids.length)
      throw Error("Ambiguous artifact identity");
    for (const step of l.transformations as Obj[])
      if (
        ![...(step.inputs as string[]), step.output].every((id) =>
          ids.includes(id as string),
        )
      )
        throw Error("Broken transformation reference");
  }
  return v as Obj;
}
export function safeSourceUrl(value: string): string | null {
  if (!/^https?:\/\//i.test(value) || /[\s\u0000-\u001f\u007f\\]/.test(value))
    return null;
  try {
    const u = new URL(value);
    return ["https:", "http:"].includes(u.protocol) &&
      !u.username &&
      !u.password &&
      !!u.hostname
      ? u.href
      : null;
  } catch {
    return null;
  }
}
