import type { DiffLine } from "$lib/types";

/** Beyond this, the line is long enough that the table costs more than the
 * marking is worth, and a line that long is rarely read word by word. */
const MAX_TOKENS = 400;

/** Below this share in common, marking the differences marks almost the whole
 * line, which says less than the row colour already does. */
const MIN_SIMILARITY = 0.35;

export type Range = [start: number, end: number];

/**
 * Which parts of a replaced line actually changed.
 *
 * A row coloured end to end says a line changed but not where, and most
 * replacements touch a word or two. Comparing by word rather than character
 * keeps the marks on things a reader recognises — an identifier, a number, an
 * argument — instead of scattering them mid-token.
 */
export function wordRanges(
  removedText: string,
  addedText: string,
): { removed: Range[]; added: Range[] } {
  const before = tokenize(removedText);
  const after = tokenize(addedText);
  const none = { removed: [], added: [] };

  if (before.length > MAX_TOKENS || after.length > MAX_TOKENS) return none;

  const common = longestCommonSubsequence(before, after);
  if (common.beforeKept.every(Boolean) && common.afterKept.every(Boolean)) {
    return none;
  }

  const shared = common.beforeKept.filter(Boolean).length;
  const longest = Math.max(before.length, after.length);
  if (longest === 0 || shared / longest < MIN_SIMILARITY) return none;

  return {
    removed: rangesOfChanged(before, common.beforeKept),
    added: rangesOfChanged(after, common.afterKept),
  };
}

/**
 * Wrap ranges of a line's plain text inside already highlighted markup.
 *
 * Offsets refer to the text a reader sees, so tags contribute nothing and an
 * escape such as `&amp;` counts as the one character it stands for. A mark is
 * closed before any tag and reopened after it, so a range crossing a
 * highlight span leaves both properly nested.
 */
export function markRanges(html: string, ranges: Range[]): string {
  if (ranges.length === 0) return html;

  let out = "";
  let position = 0;
  let plainIndex = 0;
  let rangeIndex = 0;
  let marking = false;

  const openMark = () => {
    if (!marking) {
      out += '<span class="cr-word">';
      marking = true;
    }
  };
  const closeMark = () => {
    if (marking) {
      out += "</span>";
      marking = false;
    }
  };

  while (position < html.length) {
    while (rangeIndex < ranges.length && plainIndex >= ranges[rangeIndex][1]) {
      rangeIndex += 1;
    }

    if (html[position] === "<") {
      const close = html.indexOf(">", position);
      const end = close === -1 ? html.length : close + 1;
      closeMark();
      out += html.slice(position, end);
      position = end;
      continue;
    }

    const piece = readCharacter(html, position);
    const range = ranges[rangeIndex];
    if (range && plainIndex >= range[0] && plainIndex < range[1]) openMark();
    else closeMark();

    out += piece;
    position += piece.length;
    plainIndex += 1;
  }

  closeMark();
  return out;
}

/**
 * Mark what changed inside each replaced line of a hunk.
 *
 * Removals and the additions that follow them are read as one replacement,
 * paired in order: the first removed line against the first added one. A line
 * with no counterpart is left alone, since nothing was replaced.
 */
export function applyWordMarks(lines: DiffLine[], html: string[]): string[] {
  const result = [...html];

  let index = 0;
  while (index < lines.length) {
    if (lines[index].type !== "delete") {
      index += 1;
      continue;
    }

    const removalStart = index;
    while (index < lines.length && lines[index].type === "delete") index += 1;
    const additionStart = index;
    while (index < lines.length && lines[index].type === "add") index += 1;

    const removals = additionStart - removalStart;
    const additions = index - additionStart;
    for (let offset = 0; offset < Math.min(removals, additions); offset += 1) {
      const removedAt = removalStart + offset;
      const addedAt = additionStart + offset;
      const { removed, added } = wordRanges(
        lines[removedAt].content,
        lines[addedAt].content,
      );
      result[removedAt] = markRanges(result[removedAt], removed);
      result[addedAt] = markRanges(result[addedAt], added);
    }
  }

  return result;
}

/** Split into words, runs of whitespace, and single punctuation marks. */
function tokenize(text: string): string[] {
  return text.match(/\s+|[A-Za-z0-9_]+|[^\sA-Za-z0-9_]/g) ?? [];
}

function readCharacter(html: string, at: number): string {
  if (html[at] !== "&") return html[at];
  const semicolon = html.indexOf(";", at);
  const isEntity = semicolon !== -1 && semicolon - at <= 8;
  return isEntity ? html.slice(at, semicolon + 1) : html[at];
}

function longestCommonSubsequence(
  before: string[],
  after: string[],
): { beforeKept: boolean[]; afterKept: boolean[] } {
  const rows = before.length;
  const columns = after.length;
  const table: number[][] = Array.from({ length: rows + 1 }, () =>
    new Array<number>(columns + 1).fill(0),
  );

  for (let i = rows - 1; i >= 0; i -= 1) {
    for (let j = columns - 1; j >= 0; j -= 1) {
      table[i][j] =
        before[i] === after[j]
          ? table[i + 1][j + 1] + 1
          : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }

  const beforeKept = new Array<boolean>(rows).fill(false);
  const afterKept = new Array<boolean>(columns).fill(false);
  let i = 0;
  let j = 0;
  while (i < rows && j < columns) {
    if (before[i] === after[j]) {
      beforeKept[i] = true;
      afterKept[j] = true;
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      i += 1;
    } else {
      j += 1;
    }
  }

  return { beforeKept, afterKept };
}

/** Character ranges covering the tokens that are not shared. */
function rangesOfChanged(tokens: string[], kept: boolean[]): Range[] {
  const ranges: Range[] = [];
  let offset = 0;
  let runStart: number | null = null;

  tokens.forEach((token, index) => {
    if (!kept[index]) {
      if (runStart === null) runStart = offset;
    } else if (runStart !== null) {
      ranges.push([runStart, offset]);
      runStart = null;
    }
    offset += token.length;
  });

  if (runStart !== null) ranges.push([runStart, offset]);
  return ranges;
}
