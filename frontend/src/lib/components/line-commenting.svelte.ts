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
import { type Numbering, sideIsTheReviews, whyNotTheReviews } from '$lib/anchors/numbering';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { LinePlace, LineSide, PickedLines, Thread, WrittenOnLines } from '$lib/types';
import { type DrawnHunk, type DrawnLine, NO_NUMBER } from '$lib/utils/drawn-file';
import { samePlace } from '$lib/utils/line-places';

/**
 * How the keyboard reaches a line's number. Every row has one stop, which
 * j and k move between and Tab reaches too: its new number, or its old one
 * where it shows no new one. The old number beside a new one is reached by
 * Tab when it is another line — a removed line facing the line that
 * replaced it — and left to the mouse when it is the same line.
 */
export type Reach = 'row-stop' | 'tab' | 'pointer';

/** A comment being written on lines of the file. */
type LineField = CommentField<WrittenOnLines>;

// Why no line of a file takes a comment, said by each line's number when asked, and by the file of itself
export const FILE_NOT_COMMENTABLE = 'This file cannot be commented on: its name holds control characters.';

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
	path: () => string;
	hunks: () => DrawnHunk[];
	/**
	 * Whose numbers the lines drawn carry. On a side whose numbers are not
	 * the review's own, what hangs on a line would be anchored in somebody
	 * else's numbering: its lines take no comment, and neither the threads on
	 * them nor the comments being written on them are drawn.
	 */
	numbering: () => Numbering;
	/**
	 * Whether a comment may name the file at all. A path holding a control
	 * character is drawn, but a thread naming it would be refused, and the
	 * whole round with it: its lines are only to be read.
	 */
	commentable: () => boolean;
	/**
	 * Whether the drawing stands for its file in the review: the whole of
	 * it, in the review's own numbering. Then every thread of the file is
	 * drawn here, one with no line drawn to hang under at its head. A piece
	 * cut out of the file draws the threads on its own lines and no others,
	 * and whoever draws the pieces says which hang in none; under a narrower
	 * base the notice above the diff names every thread that base cannot draw.
	 */
	standsForItsFile: () => boolean;
}

/**
 * Where a drag from `start` toward `toward` may reach: all the way, or as
 * far as the longest range allows in that direction.
 */
function reach(start: number, toward: number, longest: number): number {
	const furthest = longest - 1;
	return toward >= start ? Math.min(toward, start + furthest) : Math.max(toward, start - furthest);
}

/** The numbers of the lines drawn on each side: the places a drag can reach. */
type DrawnNumbers = Record<LineSide, ReadonlySet<number>>;

function drawnNumbers(hunks: readonly DrawnHunk[]): DrawnNumbers {
	const numbers = { old: new Set<number>(), new: new Set<number>() };
	for (const { place } of hunks.flatMap((hunk) => hunk.lines)) numbers[place.side].add(place.number);
	return numbers;
}

/**
 * How far a drag from `start` toward `toward` reaches over lines drawn one
 * after another on its side: it stops before the first number no line is
 * drawn at. A comment names every line of its span and quotes each, so a
 * span may not run over lines the reader never saw — the ones the diff left
 * out between two hunks, or on the old side a line the change kept.
 */
function furthestInRun(drawn: ReadonlySet<number>, start: number, toward: number): number {
	const step = Math.sign(toward - start);
	let reached = start;
	while (reached !== toward && drawn.has(reached + step)) reached += step;
	return reached;
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
	readonly #drawn: DrawnNumbers;
	readonly #threads: ThreadsByLine;
	readonly #unplaced: readonly Thread[];
	readonly #fields: LineField[];

	constructor(review: Review, file: DrawnFile) {
		this.#review = review;
		this.#file = file;
		this.#drawn = $derived(drawnNumbers(file.hunks()));
		this.#threads = $derived(new ThreadsByLine(review.threads.onLinesOf(file.path()), file.numbering()));
		this.#unplaced = $derived(this.#withoutTheirLine());
		this.#fields = $derived(
			review.threads.writing
				.onLinesOf(file.path())
				.filter((field) => sideIsTheReviews(field.at.lines.side, file.numbering()))
		);
	}

	/** Whether a comment may start on a line: one with a number, that nothing keeps comments off. */
	mayComment(place: LinePlace): boolean {
		return place.number !== NO_NUMBER && this.whyNot(place) === null;
	}

	/**
	 * Why no comment may start on a line, in words; null when one may: the
	 * file is not one a comment may name, or the line is on a side whose
	 * numbers are not the review's own here.
	 */
	whyNot(place: LinePlace): string | null {
		if (!this.#file.commentable()) return FILE_NOT_COMMENTABLE;
		return whyNotTheReviews(place.side, this.#file.numbering());
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
		// The field opens under the line the drag reached, following the drag
		// back up rather than staying at the furthest point
		const reached = furthestInRun(this.#drawn[drag.side], drag.start, furthest);
		this.#drag = { ...drag, end: reached, opensBelow: { side: drag.side, number: reached } };
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

	/**
	 * Threads with no line drawn here to hang under: drawn at the head of the
	 * file instead, so no thread ever leaves the screen — one on a removed
	 * line the agent put back, or on a line read in above a hunk that a new
	 * diff no longer has.
	 */
	get unplaced(): readonly Thread[] {
		return this.#unplaced;
	}

	/** The comments being written that open under a line, in the order they were started. */
	fieldsUnder(place: LinePlace): LineField[] {
		return this.#fields.filter((field) => samePlace(field.at.lines.opensBelow, place));
	}

	/** Whether anything hangs under a line: a thread, or a comment being written. */
	hasNotes(place: LinePlace): boolean {
		return this.threadsUnder(place).length > 0 || this.fieldsUnder(place).length > 0;
	}

	/**
	 * The threads of the file whose last line is not drawn here, where the
	 * drawing stands for the file; none where it does not.
	 */
	#withoutTheirLine(): readonly Thread[] {
		if (!this.#file.standsForItsFile()) return [];
		return this.#review.threads
			.onLinesOf(this.#file.path())
			.filter(({ lines }) => !this.#drawn[lines.side].has(lines.end_line))
			.map(({ thread }) => thread);
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
}
