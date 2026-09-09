import type { DiffLine } from "$lib/types";

export interface SplitCell {
  line: DiffLine;
  /** Position in the hunk's flat line list, so a comment can anchor to it. */
  index: number;
}

export interface SplitRow {
  left?: SplitCell;
  right?: SplitCell;
}

/**
 * Lay a hunk out as two columns, before on the left and after on the right.
 *
 * An unchanged line appears on both sides of one row. A run of removals is
 * faced with the run of additions that follows it, paired in order, so a
 * replacement is read across rather than down; whichever run is longer leaves
 * the other side of the surplus rows empty.
 */
export function buildSplitRows(lines: DiffLine[]): SplitRow[] {
  const rows: SplitRow[] = [];
  let index = 0;

  while (index < lines.length) {
    if (lines[index].type === "context") {
      rows.push({
        left: { line: lines[index], index },
        right: { line: lines[index], index },
      });
      index += 1;
      continue;
    }

    const removals: SplitCell[] = [];
    while (index < lines.length && lines[index].type === "delete") {
      removals.push({ line: lines[index], index });
      index += 1;
    }

    const additions: SplitCell[] = [];
    while (index < lines.length && lines[index].type === "add") {
      additions.push({ line: lines[index], index });
      index += 1;
    }

    const height = Math.max(removals.length, additions.length);
    for (let offset = 0; offset < height; offset += 1) {
      rows.push({ left: removals[offset], right: additions[offset] });
    }
  }

  return rows;
}
