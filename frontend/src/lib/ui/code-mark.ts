/**
 * A mark over a stretch of the code (CodeMark): its ground under the words,
 * drawn by a highlight of the page so the line's markup stays as it is, and,
 * where the mark is the reader's chip, an edge round it. A highlight draws a
 * ground and no edge, so the edge is drawn over the code, a box to each line
 * the stretch stands on, read where the stretch stands now.
 */

import type { CodeMark } from '$lib/dom/code-marks';
import { type AreaBox, boxInArea, sameBox } from '$lib/dom/scroll-area';

/**
 * Whether each mark is edged: the name pressed and the name arrived at are
 * the reader's chip, edged; the word under the pointer while the key is held
 * is on the ink's tint, with no edge.
 */
export const EDGED: Record<CodeMark, boolean> = { held: false, pressed: true, arrived: true };

/** Whether two boxes on the screen stand on one line: each reaches into the other's height. */
function onOneLine(first: DOMRectReadOnly, second: DOMRectReadOnly): boolean {
	return first.top < second.bottom && second.top < first.bottom;
}

/** The box round two boxes. */
function joined(first: DOMRectReadOnly, second: DOMRectReadOnly): DOMRectReadOnly {
	const left = Math.min(first.left, second.left);
	const top = Math.min(first.top, second.top);
	const right = Math.max(first.right, second.right);
	const bottom = Math.max(first.bottom, second.bottom);
	return new DOMRect(left, top, right - left, bottom - top);
}

/**
 * The boxes of a stretch, one to each line it stands on: the browser gives a
 * box to each piece of its text, and a name split by the highlighter's or the
 * change's marks is pieces side by side on one line.
 */
function linesOf(stretch: Range): DOMRectReadOnly[] {
	const lines: DOMRectReadOnly[] = [];
	for (const piece of stretch.getClientRects()) {
		const last = lines.at(-1);
		if (last !== undefined && onOneLine(last, piece)) lines[lines.length - 1] = joined(last, piece);
		else lines.push(piece);
	}
	return lines;
}

/** The boxes of a stretch's edge, where it stands now, in the room of the layer they are drawn on. */
export function edgeBoxes(stretch: Range, layer: HTMLElement): AreaBox[] {
	return linesOf(stretch).map((line) => boxInArea(layer, line));
}

/** Whether an edge read again stands as it stood: as many boxes, each one of those before. */
export function sameEdge(read: readonly AreaBox[], before: readonly AreaBox[]): boolean {
	return read.length === before.length && read.every((box) => before.some((stood) => sameBox(box, stood)));
}
