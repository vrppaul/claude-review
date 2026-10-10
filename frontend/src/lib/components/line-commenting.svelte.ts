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
import { lineAnchor } from '$lib/anchors/line';
import { lineRangeLabel } from '$lib/anchors/line-label';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { CommentSeverity, LinePlace, LineSide, PickedLines, Thread, WrittenOnLines } from '$lib/types';
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
	path: () => string;
	hunks: () => DrawnHunk[];
	/**
	 * Whether the removed lines on screen are the review's own. Under a
	 * narrower base the left-hand side belongs to that base, so a thread on a
	 * removed line there would be anchored in somebody else's numbering:
	 * removed lines then take no comment, and the threads on them are not
	 * drawn. A story step reads the review's own diff, so its are.
	 */
	reviewOwnsRemovedLines: () => boolean;
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
		this.#fields = $derived(review.threads.writing.onLinesOf(file.path()));
	}

	/** Where a comment being written hangs, said above its field. */
	labelOf(field: LineField): string {
		const { side, startLine, endLine } = field.at.lines;
		return lineRangeLabel(side, startLine, endLine);
	}

	/** What a comment's lines say now: it quotes them, and a suggestion starts from them. */
	quoteOf(field: LineField): string[] {
		return this.#file
			.hunks()
			.flatMap((hunk) => hunk.lines)
			.filter(({ place }) => isPicked(place, field.at.lines))
			.map(({ line }) => line.content);
	}

	/** Whether a comment may start on a line: one with a number, and a removed one only if it is the review's. */
	mayComment(place: LinePlace): boolean {
		if (place.number === NO_NUMBER) return false;
		return place.side !== 'old' || this.#file.reviewOwnsRemovedLines();
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
		const end = reach(drag.start, drawn.place.number, this.#review.longestQuotedRange);
		const reached = { side: drag.side, number: end };
		// The field opens under the line the drag reached, following the drag
		// back up rather than staying at the furthest point; a drag stopped
		// short of the pointer opens it where the drag stopped, if that line
		// is drawn
		this.#drag = { ...drag, end, opensBelow: this.#isDrawn(reached) ? reached : drag.opensBelow };
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

	/**
	 * Add a comment to the review. The lines travel with it: once the diff
	 * is taken again they are how the thread finds where it belongs.
	 */
	save(field: LineField, body: string, severity: CommentSeverity, images: string[]): void {
		this.#write(field, body, severity, images);
		this.#review.threads.writing.added(field);
	}

	/** Add a comment and hand it straight to whoever is answering. */
	async ask(field: LineField, body: string, severity: CommentSeverity, images: string[]): Promise<void> {
		const written = this.#write(field, body, severity, images);
		this.#review.threads.writing.asked(field);
		try {
			await this.#review.threads.ask(written);
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
	}

	/** Put a comment being written away unsaid. */
	cancel(field: LineField): void {
		this.#review.threads.writing.discard(field);
	}

	#pick(lines: PickedLines): void {
		this.#review.threads.writing.pickLines(this.#file.path(), lines);
	}

	/** Write a comment on its lines; its thread's id. */
	#write(field: LineField, body: string, severity: CommentSeverity, images: string[]): string {
		const { side, startLine, endLine } = field.at.lines;
		const anchor = lineAnchor(this.#file.path(), side, startLine, endLine, this.quoteOf(field));
		return this.#review.threads.add({ anchor, body, severity, images });
	}

	#isDrawn(place: LinePlace): boolean {
		return this.#file.hunks().some((hunk) => hunk.lines.some((drawn) => samePlace(drawn.place, place)));
	}
}
