import type example from "../public/data/submission-period-v1.json";
import pin from "./submission-pin.json";
import { loadBounded, verifyPreviewBytes } from "./data";
export type SubmissionReport = typeof example;
// Exact byte admission, not a general-purpose report/real-source input API.
export async function verifySubmission(raw: string): Promise<SubmissionReport> {
  await verifyPreviewBytes(raw, pin.sha256);
  const data = JSON.parse(raw) as SubmissionReport;
  if (
    data.contract !== "civictrace-synthetic-submission-period/1" ||
    data.synthetic !== true ||
    data.analytics_enabled !== false
  )
    throw Error("Only reviewed synthetic report supported");
  return data;
}
export function loadSubmission(signal: AbortSignal): Promise<SubmissionReport> {
  return loadBounded(
    "data/submission-period-v1.json",
    verifySubmission,
    signal,
  );
}
