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
	 * The most lines one comment may cover, as the server says. A comment
	 * quotes every line it covers, and the server refuses a quote longer than
	 * this — so a drag simply stops there.
	 */
	longestRange: () => number;
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
function reach(start: number, toward: number, longest: number): number {
	const furthest = longest - 1;
	return toward >= start ? Math.min(toward, start + furthest) : Math.max(toward, start - furthest);
}

/** Whether a line number lies between two others, whichever way round they are. */
function isBetween(lineNumber: number, one: number, other: number): boolean {
	return lineNumber >= Math.min(one, other) && lineNumber <= Math.max(one, other);
}

/** A drag across lines of one side, from where it began to where it has reached. */
interface Drag {
	side: LineSide;
	start: number;
	end: number;
	/** Which of the file's lines the comment field opens below once the drag is let go. */
	opensBelow: number;
}

/** What the reader is selecting to comment on, within what they may select. */
export class LineSelection {
	readonly #rules: SelectionRules;
	#commentingAt = $state<LineRange | null>(null);
	#drag = $state<Drag | null>(null);

	constructor(rules: SelectionRules) {
		this.#rules = rules;
	}

	/** The lines the comment field is open on, if it is open. */
	get commentingAt(): LineRange | null {
		return this.#commentingAt;
	}

	get dragging(): boolean {
		return this.#drag !== null;
	}

	reset(): void {
		this.#commentingAt = null;
		this.#drag = null;
	}

	handleMouseDown(line: DiffLine, index: number): void {
		if (!this.#mayComment(line)) return;
		const lineNumber = getLineNumber(line);
		this.#drag = { side: lineSide(line), start: lineNumber, end: lineNumber, opensBelow: index };
	}

	handleMouseEnter(line: DiffLine, index: number): void {
		const drag = this.#drag;
		// A range spans one side only: old line 42 and new line 42 are different
		// places, so dragging across the other side must not extend the range.
		if (drag === null || lineSide(line) !== drag.side) return;
		const lineNumber = getLineNumber(line);
		if (lineNumber === 0) return;
		const end = reach(drag.start, lineNumber, this.#rules.longestRange());
		// The composer opens under the row the drag reaches, so this follows the
		// drag back up rather than staying at the furthest point it reached —
		// and when the pointer is past where the drag may reach, it opens under
		// the row the drag stopped at
		const opensBelow = end === lineNumber ? index : (this.#rules.rowOf(drag.side, end) ?? drag.opensBelow);
		this.#drag = { ...drag, end, opensBelow };
	}

	handleMouseUp(): void {
		const drag = this.#drag;
		if (drag === null) return;
		this.#drag = null;
		this.#commentingAt = {
			side: drag.side,
			startLine: Math.min(drag.start, drag.end),
			endLine: Math.max(drag.start, drag.end),
			opensBelow: drag.opensBelow
		};
	}

	/** Open the composer on one line, without a drag — the keyboard path. */
	commentOnLine(line: DiffLine, index: number): void {
		if (!this.#mayComment(line)) return;
		const lineNumber = getLineNumber(line);
		this.#drag = null;
		this.#commentingAt = { side: lineSide(line), startLine: lineNumber, endLine: lineNumber, opensBelow: index };
	}

	clearCommenting(): void {
		this.#commentingAt = null;
	}

	isHighlighted(side: LineSide, lineNumber: number): boolean {
		const drag = this.#drag;
		if (drag !== null && drag.side === side && isBetween(lineNumber, drag.start, drag.end)) return true;
		const at = this.#commentingAt;
		return at !== null && at.side === side && isBetween(lineNumber, at.startLine, at.endLine);
	}

	/** Whether a comment may start on a line: one with a number, and a removed one only where the rules allow it. */
	#mayComment(line: DiffLine): boolean {
		if (getLineNumber(line) === 0) return false;
		return lineSide(line) !== 'old' || this.#rules.mayCommentOnRemoved();
	}
}
