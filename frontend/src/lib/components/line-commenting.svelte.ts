/**
 * Commenting on the lines of one drawn file: picking them with the mouse or
 * the keyboard, marking what is picked, and what hangs under each line — its
 * threads, and the comment being written there.
 *
 * One for every drawing of a file, in whichever layout: both layouts pick,
 * mark and write the same way, and differ only in where a line's cells are.
 */

import { ThreadsByLine } from '$lib/anchors/comment-index';
import { lineAnchor } from '$lib/anchors/line';
import { lineRangeLabel } from '$lib/anchors/line-label';
import type { Review } from '$lib/review/review.svelte';
import type { CommentSeverity, LinePlace, LineSide, Thread } from '$lib/types';
import { type DrawnHunk, type DrawnLine, NO_NUMBER, samePlace } from '$lib/utils/drawn-file';

/** Lines picked to comment on, and the line the comment field opens under. */
export interface PickedLines {
	side: LineSide;
	startLine: number;
	endLine: number;
	/** Where the drag ended, so the field opens beside the pointer rather than at the far end of a long range. */
	opensBelow: LinePlace;
}

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

/** What picked lines say now, as drawn. */
function quoteOf(hunks: DrawnHunk[], picked: PickedLines): string[] {
	return hunks
		.flatMap((hunk) => hunk.lines)
		.filter(({ place }) => place.side === picked.side && isBetween(place.number, picked.startLine, picked.endLine))
		.map(({ line }) => line.content);
}

export class LineCommenting {
	readonly #review: Review;
	readonly #file: DrawnFile;
	#drag = $state<Drag | null>(null);
	#picked = $state<PickedLines | null>(null);
	readonly #threads: ThreadsByLine;
	readonly #quote: string[];

	constructor(review: Review, file: DrawnFile) {
		this.#review = review;
		this.#file = file;
		this.#threads = $derived(
			new ThreadsByLine(review.threads.onFile(file.path()), file.path(), file.reviewOwnsRemovedLines())
		);
		this.#quote = $derived(this.#picked === null ? [] : quoteOf(file.hunks(), this.#picked));
	}

	/** Where the comment being written hangs, said above its field. */
	get label(): string | undefined {
		const picked = this.#picked;
		return picked === null ? undefined : lineRangeLabel(picked.side, picked.startLine, picked.endLine);
	}

	/** What the picked lines say now: the comment quotes them, and a suggestion starts from them. */
	get quote(): string[] {
		return this.#quote;
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

	/** The pointer was let go, anywhere: the lines dragged over are picked. */
	release(): void {
		const drag = this.#drag;
		if (drag === null) return;
		this.#drag = null;
		this.#picked = {
			side: drag.side,
			startLine: Math.min(drag.start, drag.end),
			endLine: Math.max(drag.start, drag.end),
			opensBelow: drag.opensBelow
		};
	}

	/** Pick one line, without a drag — the keyboard's way. */
	commentOn(drawn: DrawnLine): void {
		if (!this.mayComment(drawn.place)) return;
		const { side, number } = drawn.place;
		this.#drag = null;
		this.#picked = { side, startLine: number, endLine: number, opensBelow: drawn.place };
	}

	/**
	 * Whether a line is marked as picked or being dragged over. The mark is
	 * added to the line's change rather than replacing it: a line keeps
	 * showing what changed on it while it is written about.
	 */
	isMarked(place: LinePlace): boolean {
		const drag = this.#drag;
		if (drag !== null && drag.side === place.side && isBetween(place.number, drag.start, drag.end)) return true;
		const picked = this.#picked;
		return picked !== null && picked.side === place.side && isBetween(place.number, picked.startLine, picked.endLine);
	}

	/** The threads hanging under a line. */
	threadsUnder(place: LinePlace): readonly Thread[] {
		return this.#threads.at(place);
	}

	/** Whether the comment being written opens under a line. */
	opensUnder(place: LinePlace): boolean {
		return this.#picked !== null && samePlace(this.#picked.opensBelow, place);
	}

	/** Whether anything hangs under a line: a thread, or the comment being written. */
	hasNotes(place: LinePlace): boolean {
		return this.threadsUnder(place).length > 0 || this.opensUnder(place);
	}

	/**
	 * Add the comment to the review. The lines travel with it: once the diff
	 * is taken again they are how the thread finds where it belongs.
	 */
	save(body: string, severity: CommentSeverity, images: string[]): void {
		this.#write(body, severity, images);
	}

	/** Add the comment and hand it straight to whoever is answering. */
	async ask(body: string, severity: CommentSeverity, images: string[]): Promise<void> {
		const written = this.#write(body, severity, images);
		if (written === null) return;
		try {
			await this.#review.threads.ask(written);
		} catch {
			// The comment is written either way; the thread offers to ask again
		}
	}

	/** Put the comment being written away unwritten. */
	cancel(): void {
		this.#picked = null;
	}

	/** Write the comment on the picked lines; its thread's id, or null with nothing picked. */
	#write(body: string, severity: CommentSeverity, images: string[]): string | null {
		const picked = this.#picked;
		if (picked === null) return null;
		const { side, startLine, endLine } = picked;
		const anchor = lineAnchor(this.#file.path(), side, startLine, endLine, this.#quote);
		this.#picked = null;
		return this.#review.threads.add({ anchor, body, severity, images });
	}

	#isDrawn(place: LinePlace): boolean {
		return this.#file.hunks().some((hunk) => hunk.lines.some((drawn) => samePlace(drawn.place, place)));
	}
}
