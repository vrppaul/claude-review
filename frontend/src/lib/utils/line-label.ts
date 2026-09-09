import type { LineSide } from "$lib/types";

/**
 * Human label for a commented range: "Line 42", "Lines 42-47", or the
 * "Removed" variants. Comments on the old side point at lines the change
 * deleted, so their numbers refer to the file as it was.
 */
export function lineRangeLabel(
  side: LineSide,
  startLine: number,
  endLine: number,
): string {
  const removed = side === "old";
  if (endLine !== startLine) {
    return `${removed ? "Removed lines" : "Lines"} ${startLine}-${endLine}`;
  }
  return `${removed ? "Removed line" : "Line"} ${startLine}`;
}

/**
 * Compact reference used next to a file path: "42", "42-47", "42 (removed)".
 * Matches the wording the submitted review uses, so the preview and the
 * output the agent reads say the same thing.
 */
export function lineRefLabel(
  side: LineSide,
  startLine: number,
  endLine: number,
): string {
  const span =
    endLine !== startLine ? `${startLine}-${endLine}` : `${startLine}`;
  return side === "old" ? `${span} (removed)` : span;
}
