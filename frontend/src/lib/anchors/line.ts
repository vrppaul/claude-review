import type { LineAnchor, LineSide } from "$lib/types";
import type { AnchorView } from "$lib/anchors/views";
import { diffStore } from "$lib/stores/diff.svelte";
import { lineRangeLabel } from "$lib/utils/line-label";
import { scrollToComment } from "$lib/utils/scroll";

function fileName(path: string): string {
  return path.split("/").pop() ?? path;
}

function label(anchor: LineAnchor): string {
  return lineRangeLabel(anchor.side, anchor.start_line, anchor.end_line);
}

/** How a thread on lines of a file is named and brought into view. */
export const lineAnchorView: AnchorView<LineAnchor> = {
  label,
  place: (anchor) => `${anchor.file} · ${label(anchor)}`,
  shortPlace: (anchor) => `${fileName(anchor.file)} ${label(anchor)}`,
  token: (anchor) => `@${anchor.file}:${anchor.start_line}-${anchor.end_line}`,
  side: (anchor) => anchor.side,
  reveal(threadId, anchor) {
    // A folded file has no thread on screen to move to, so it is opened first
    if (diffStore.isCollapsed(anchor.file))
      diffStore.toggleCollapsed(anchor.file);
    requestAnimationFrame(() => scrollToComment(threadId, anchor.file));
  },
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
