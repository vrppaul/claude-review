import type { DiffLine, LineSide } from '$lib/types';

export interface LineRange {
	side: LineSide;
	startLine: number;
	endLine: number;
	/** Which of the file's lines, counted end to end across its hunks, the comment field opens below. */
	opensBelow: number;
}

/** A removed line only exists in the old file; everything else is the new one. */
export function lineSide(line: DiffLine): LineSide {
	return line.kind === 'delete' ? 'old' : 'new';
}

/** The number a line carries on its own side — old for removed, new otherwise. */
export function getLineNumber(line: DiffLine): number {
	return line.new_number ?? line.old_number ?? 0;
}

/** What the reader may select, asked afresh each time it matters. */
export interface SelectionRules {
	/**
	 * Whether a removed line may be commented on. Under a narrower base the
	 * left-hand side of the diff belongs to that base, not to the review, so a
	 * thread written on a removed line there would be anchored in somebody
	 * else's numbering — and hidden the moment it was saved, because that is
	 * what the drawing rule does with it.
	 */
	mayCommentOnRemoved: () => boolean;
	/**
	 * The most lines one comment may cover, as the server says; null before it
	 * has. A comment quotes every line it covers, and the server refuses a
	 * quote longer than this — so a drag simply stops there.
	 */
	longestRange: () => number | null;
	/**
	 * Where a line stands among the rows on screen, so a drag stopped short of
	 * the pointer opens the comment under the row it stopped at. Undefined for
	 * a line the diff does not show.
	 */
	rowOf: (side: LineSide, lineNumber: number) => number | undefined;
}

/** Where a line stands among a file's rows, counted as the views count them. */
export function rowOfLine(rows: DiffLine[], side: LineSide, lineNumber: number): number | undefined {
	const row = rows.findIndex((line) => lineSide(line) === side && getLineNumber(line) === lineNumber);
	return row === -1 ? undefined : row;
}

/**
 * Where a drag from `start` toward `toward` may reach: all the way, or as
 * far as the longest range allows in that direction.
 */
function reach(start: number, toward: number, longest: number | null): number {
	if (longest === null) return toward;
	const furthest = longest - 1;
	return toward >= start ? Math.min(toward, start + furthest) : Math.max(toward, start - furthest);
}

/** Track what the reader is selecting, within what they may select. */
export function createLineSelection(rules: SelectionRules) {
	let commentingAt = $state<LineRange | null>(null);
	let dragSide = $state<LineSide | null>(null);
	let dragStart = $state<number | null>(null);
	let dragEnd = $state<number | null>(null);
	let dragOpensBelow = $state<number | null>(null);
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
			dragSide = null;
			dragStart = null;
			dragEnd = null;
			dragOpensBelow = null;
			dragging = false;
		},

		handleMouseDown(line: DiffLine, index: number) {
			const lineNumber = getLineNumber(line);
			if (lineNumber === 0) return;
			if (lineSide(line) === 'old' && !rules.mayCommentOnRemoved()) return;
			dragSide = lineSide(line);
			dragStart = lineNumber;
			dragEnd = lineNumber;
			dragOpensBelow = index;
			dragging = true;
		},

		handleMouseEnter(line: DiffLine, index: number) {
			if (!dragging) return;
			// A range spans one side only: old line 42 and new line 42 are different
			// places, so dragging across the other side must not extend the range.
			if (lineSide(line) !== dragSide) return;
			const lineNumber = getLineNumber(line);
			if (lineNumber === 0 || dragStart === null) return;
			dragEnd = reach(dragStart, lineNumber, rules.longestRange());
			// The composer opens under the row the drag reaches, so this follows the
			// drag back up rather than staying at the furthest point it reached —
			// and when the pointer is past where the drag may reach, it opens under
			// the row the drag stopped at
			dragOpensBelow = dragEnd === lineNumber ? index : (rules.rowOf(lineSide(line), dragEnd) ?? dragOpensBelow);
		},

		handleMouseUp() {
			if (!dragging || dragStart === null || dragEnd === null || dragSide === null) return;
			dragging = false;
			commentingAt = {
				side: dragSide,
				startLine: Math.min(dragStart, dragEnd),
				endLine: Math.max(dragStart, dragEnd),
				opensBelow: dragOpensBelow ?? 0
			};
			dragSide = null;
			dragStart = null;
			dragEnd = null;
			dragOpensBelow = null;
		},

		/** Open the composer on one line, without a drag — the keyboard path. */
		commentOnLine(line: DiffLine, index: number) {
			const lineNumber = getLineNumber(line);
			if (lineNumber === 0) return;
			if (lineSide(line) === 'old' && !rules.mayCommentOnRemoved()) return;
			dragging = false;
			commentingAt = {
				side: lineSide(line),
				startLine: lineNumber,
				endLine: lineNumber,
				opensBelow: index
			};
		},

		clearCommenting() {
			commentingAt = null;
		},

		isHighlighted(side: LineSide, lineNumber: number): boolean {
			if (dragging && dragSide === side && dragStart !== null && dragEnd !== null) {
				if (lineNumber >= Math.min(dragStart, dragEnd) && lineNumber <= Math.max(dragStart, dragEnd)) {
					return true;
				}
			}
			if (commentingAt !== null && commentingAt.side === side) {
				return lineNumber >= commentingAt.startLine && lineNumber <= commentingAt.endLine;
			}
			return false;
		}
	};
}
