/**
 * Commenting on the lines of one drawn file: picking them with the mouse or
 * the keyboard, marking what is picked, and what hangs under each line — its
 * threads, and the comments being written there.
 *
 * One for every drawing of a file, in whichever layout: both layouts pick,
 * mark and write the same way, and differ only in where a line's cells are.
 * A drag belongs to the drawing it happens in; the comments it starts belong
 * to the review, which keeps them while drawings come and go.
 */

import { ThreadsByLine } from '$lib/anchors/comment-index';
import { sideIsDrawn } from '$lib/anchors/placement';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { LinePlace, LineSide, PickedLines, Thread, WrittenOnLines } from '$lib/types';
import { type DrawnHunk, type DrawnLine, NO_NUMBER, samePlace } from '$lib/utils/drawn-file';

/** A comment being written on lines of the file. */
type LineField = CommentField<WrittenOnLines>;

/** A drag across lines of one side, from where it began to where it has reached. */
interface Drag {
	side: LineSide;
	start: number;
	end: number;
	/** The line the comment field opens under once the drag is let go. */
	opensBelow: LinePlace;
}

/** The file a drawing shows, read afresh each time it matters. */
export interface DrawnFile {
	path(): string;
	hunks(): DrawnHunk[];
	/**
	 * Whether the removed lines on screen are the review's own. Under a
	 * narrower base the left-hand side belongs to that base, so what hangs on
	 * a removed line there would be anchored in somebody else's numbering:
	 * removed lines then take no comment, and neither the threads on them nor
	 * the comments being written on them are drawn. A story step reads the
	 * review's own diff, so its are.
	 */
	reviewOwnsRemovedLines(): boolean;
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

/** Whether a line is among picked lines. */
function isPicked(place: LinePlace, picked: PickedLines): boolean {
	return place.side === picked.side && isBetween(place.number, picked.startLine, picked.endLine);
}

export class LineCommenting {
	readonly #review: Review;
	readonly #file: DrawnFile;
	#drag = $state<Drag | null>(null);
	readonly #threads: ThreadsByLine;
	readonly #fields: LineField[];

	constructor(review: Review, file: DrawnFile) {
		this.#review = review;
		this.#file = file;
		this.#threads = $derived(
			new ThreadsByLine(review.threads.onFile(file.path()), file.path(), file.reviewOwnsRemovedLines())
		);
		this.#fields = $derived(
			review.threads.writing
				.onLinesOf(file.path())
				.filter((field) => sideIsDrawn(field.at.lines.side, file.reviewOwnsRemovedLines()))
		);
	}

	/** Whether a comment may start on a line: one with a number, on a side whose comments are drawn here. */
	mayComment(place: LinePlace): boolean {
		return place.number !== NO_NUMBER && sideIsDrawn(place.side, this.#file.reviewOwnsRemovedLines());
	}

	/** The pointer went down on a line: a drag starts there. */
	press(drawn: DrawnLine): void {
		if (!this.mayComment(drawn.place)) return;
		const { side, number } = drawn.place;
		this.#drag = { side, start: number, end: number, opensBelow: drawn.place };
	}

	/** The pointer came onto a line: a drag reaches it, as far as one comment may. */
	enter(drawn: DrawnLine): void {
		const drag = this.#drag;
		// A range spans one side only: old line 42 and new line 42 are different
		// places, so dragging across the other side must not extend the range.
		if (drag === null || drawn.place.side !== drag.side || drawn.place.number === NO_NUMBER) return;
		const furthest = reach(drag.start, drawn.place.number, this.#review.longestQuotedRange);
		// A drag stopped short of the pointer stops on a line of its side that is
		// drawn: on the old side the line at the furthest number may be one the
		// change kept, which is on the new side, and nothing would hang under it.
		// The field opens under the line the drag reached, following the drag
		// back up rather than staying at the furthest point.
		const reached = this.#furthestDrawn(drag.side, drag.start, furthest);
		this.#drag = { ...drag, end: reached.number, opensBelow: reached };
	}

	/** The pointer was let go, anywhere: a comment is started on the lines dragged over. */
	release(): void {
		const drag = this.#drag;
		if (drag === null) return;
		this.#drag = null;
		this.#pick({
			side: drag.side,
			startLine: Math.min(drag.start, drag.end),
			endLine: Math.max(drag.start, drag.end),
			opensBelow: drag.opensBelow
		});
	}

	/** Start a comment on one line, without a drag — the keyboard's way. */
	commentOn(drawn: DrawnLine): void {
		if (!this.mayComment(drawn.place)) return;
		const { side, number } = drawn.place;
		this.#drag = null;
		this.#pick({ side, startLine: number, endLine: number, opensBelow: drawn.place });
	}

	/**
	 * Whether a line is marked: dragged over, or written about. The mark is
	 * added to the line's change rather than replacing it: a line keeps
	 * showing what changed on it while it is written about.
	 */
	isMarked(place: LinePlace): boolean {
		const drag = this.#drag;
		if (drag !== null && drag.side === place.side && isBetween(place.number, drag.start, drag.end)) return true;
		return this.#fields.some((field) => isPicked(place, field.at.lines));
	}

	/** The threads hanging under a line. */
	threadsUnder(place: LinePlace): readonly Thread[] {
		return this.#threads.at(place);
	}

	/** The comments being written that open under a line, in the order they were started. */
	fieldsUnder(place: LinePlace): LineField[] {
		return this.#fields.filter((field) => samePlace(field.at.lines.opensBelow, place));
	}

	/** Whether anything hangs under a line: a thread, or a comment being written. */
	hasNotes(place: LinePlace): boolean {
		return this.threadsUnder(place).length > 0 || this.fieldsUnder(place).length > 0;
	}

	/** Start a comment on picked lines, quoting what they say as they are picked. */
	#pick(lines: PickedLines): void {
		const quote = this.#file
			.hunks()
			.flatMap((hunk) => hunk.lines)
			.filter(({ place }) => isPicked(place, lines))
			.map(({ line }) => line.content);
		this.#review.threads.writing.pickLines(this.#file.path(), lines, quote);
	}

	/** The line of a side drawn here furthest from `start` toward `end`; `start`'s own when none is further. */
	#furthestDrawn(side: LineSide, start: number, end: number): LinePlace {
		return this.#file
			.hunks()
			.flatMap((hunk) => hunk.lines)
			.map(({ place }) => place)
			.filter((place) => place.side === side && isBetween(place.number, start, end))
			.reduce(
				(furthest, place) => (Math.abs(place.number - start) > Math.abs(furthest.number - start) ? place : furthest),
				{ side, number: start }
			);
	}
}
