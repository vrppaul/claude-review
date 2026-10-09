import type { LineAnchor, LineSide } from "$lib/types";
import type { AnchorView } from "$lib/anchors/views";
import { lineRangeLabel } from "$lib/utils/line-label";

function fileName(path: string): string {
  return path.split("/").pop() ?? path;
}

function label(anchor: LineAnchor): string {
  return lineRangeLabel(anchor.side, anchor.start_line, anchor.end_line);
}

/** How a thread on lines of a file is named. */
export const lineAnchorView: AnchorView<LineAnchor> = {
  label,
  place: (anchor) => `${anchor.file} · ${label(anchor)}`,
  shortPlace: (anchor) => `${fileName(anchor.file)} ${label(anchor)}`,
  token: (anchor) => `@${anchor.file}:${anchor.start_line}-${anchor.end_line}`,
  side: (anchor) => anchor.side,
};

/** Lines of a file as the reader selects them, with what they say now. */
export function lineAnchor(
  file: string,
  side: LineSide,
  startLine: number,
  endLine: number,
  quote: string[],
): LineAnchor {
  return {
    kind: "line",
    file,
    side,
    start_line: startLine,
    end_line: endLine,
    quote,
    outdated: false,
  };
}
