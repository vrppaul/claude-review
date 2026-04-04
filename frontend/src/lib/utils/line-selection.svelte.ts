import type { DiffLine } from '$lib/types';

export interface LineRange {
	line: number;
	endLine: number;
	/** Index of the last line in the flat hunk lines array where the comment box should render */
	anchorIndex: number;
}

function getLineNumber(line: DiffLine): number {
	return line.new_no ?? line.old_no ?? 0;
}

export function createLineSelection() {
	let commentingAt = $state<LineRange | null>(null);
	let dragStart = $state<number | null>(null);
	let dragEnd = $state<number | null>(null);
	let dragAnchorIndex = $state<number | null>(null);
	let dragging = $state(false);

	return {
		get commentingAt() {
			return commentingAt;
		},
		get dragging() {
			return dragging;
		},

		reset() {
			commentingAt = null;
			dragStart = null;
			dragEnd = null;
			dragging = false;
		},

		handleMouseDown(line: DiffLine, index: number) {
			const lineNo = getLineNumber(line);
			if (lineNo === 0) return;
			dragStart = lineNo;
			dragEnd = lineNo;
			dragAnchorIndex = index;
			dragging = true;
		},

		handleMouseEnter(line: DiffLine, index: number) {
			if (!dragging) return;
			const lineNo = getLineNumber(line);
			if (lineNo === 0) return;
			dragEnd = lineNo;
			dragAnchorIndex = Math.max(dragAnchorIndex ?? index, index);
		},

		handleMouseUp() {
			if (!dragging || dragStart === null || dragEnd === null) return;
			dragging = false;
			const start = Math.min(dragStart, dragEnd);
			const end = Math.max(dragStart, dragEnd);
			commentingAt = { line: start, endLine: end, anchorIndex: dragAnchorIndex ?? 0 };
			dragStart = null;
			dragEnd = null;
			dragAnchorIndex = null;
		},

		clearCommenting() {
			commentingAt = null;
		},

		isHighlighted(lineNo: number): boolean {
			if (dragging && dragStart !== null && dragEnd !== null) {
				const start = Math.min(dragStart, dragEnd);
				const end = Math.max(dragStart, dragEnd);
				if (lineNo >= start && lineNo <= end) return true;
			}
			if (commentingAt !== null) {
				if (lineNo >= commentingAt.line && lineNo <= commentingAt.endLine) return true;
			}
			return false;
		},

		getLineNumber
	};
}
