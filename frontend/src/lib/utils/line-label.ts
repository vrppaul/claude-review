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
