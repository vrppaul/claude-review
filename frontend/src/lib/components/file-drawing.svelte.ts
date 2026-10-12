/**
 * A file made ready to draw, in whichever layout: its lines, commenting on
 * them, and reading in what the diff left out around its hunks — the whole
 * of the file, or a piece cut out of it, which has nothing around it to read.
 *
 * Made once by whoever draws the file and handed to the layout, so both
 * layouts lay out the same lines, and switching between them prepares
 * nothing again.
 */

import { type DrawnFile, LineCommenting } from '$lib/components/line-commenting.svelte';
import type { RevealedContext } from '$lib/review/revealed-context.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { DiffFile } from '$lib/types';
import { type DrawnHunk, drawnHunks } from '$lib/utils/drawn-file';
import { type ContextGap, gapBelow, type GapRead, readOf, type Widening, withRevealed } from '$lib/utils/expansions';

/** How a file's lines are drawn: rendered, rendered beside their text, in two columns, or in one. */
export type FileView = 'preview' | 'side-by-side' | 'split' | 'raw';

/** A file drawn whole, as the diff on screen has it. */
interface WholeFile {
	kind: 'whole';
	/** Whether the removed lines on screen are the review's own: see `DrawnFile`. */
	reviewOwnsRemovedLines: boolean;
	/** Where the lines read in around its hunks are kept. */
	revealed: RevealedContext;
}

/**
 * A piece of a file, cut out of the review's own diff: a step of a story.
 * Its removed lines are the review's own whatever base is on screen, and
 * what lies around it is the rest of its file, which it does not read in.
 */
interface Piece {
	kind: 'piece';
}

/** How much of a file a drawing is of: the whole of it, or a piece. */
export type Extent = WholeFile | Piece;

/** A piece, which has no more to say of itself than that it is one. */
export const A_PIECE: Extent = { kind: 'piece' };

/** What a file is drawn from and by, read afresh each time it matters. */
export interface DrawingSource {
	file: () => DiffFile;
	/** What it is highlighted as, if anything. */
	language: () => string | null;
	/** How much of the file is drawn. */
	extent: () => Extent;
}

export class FileDrawing implements DrawnFile {
	readonly commenting: LineCommenting;
	readonly #review: Review;
	readonly #source: DrawingSource;
	readonly #shownFile: DiffFile;
	readonly #hunks: DrawnHunk[];
	readonly #end: ContextGap | null;

	constructor(review: Review, source: DrawingSource) {
		this.#review = review;
		this.#source = source;
		// Lines revealed from the file sit inside the hunk beside which they were
		// read, so numbering, highlighting and anchoring need no special case
		this.#shownFile = $derived(this.#shown());
		// What changed inside a replaced line is marked in a diff, where lines are replaced
		this.#hunks = $derived(drawnHunks(this.#shownFile, source.language(), review.mode === 'diff'));
		this.#end = $derived(this.#gapAtTheEnd());
		this.commenting = new LineCommenting(review, this);
	}

	path(): string {
		return this.#source.file().path;
	}

	hunks(): DrawnHunk[] {
		return this.#hunks;
	}

	reviewOwnsRemovedLines(): boolean {
		const extent = this.#source.extent();
		return extent.kind === 'piece' || extent.reviewOwnsRemovedLines;
	}

	commentable(): boolean {
		return this.#source.file().commentable;
	}

	piece(): boolean {
		return this.#source.extent().kind === 'piece';
	}

	/**
	 * Whether a gap is this drawing's to say. A piece says what it leaves
	 * out between its own hunks; what lies above its first and below its
	 * last is the rest of the file, which it does not draw.
	 */
	says(gap: ContextGap): boolean {
		return !this.piece() || (gap.above !== null && gap.below !== null);
	}

	/** Whether what the diff left out may be read in here, or only said: a piece reads nothing in. */
	get readsGaps(): boolean {
		return this.#revealed() !== null;
	}

	/** The gap below the last hunk, where the file may go on past it; null where it cannot. */
	get end(): ContextGap | null {
		return this.#end;
	}

	/** Whether the lines of a gap are on their way. */
	isReading(gap: ContextGap): boolean {
		return this.#revealed()?.isReading(this.path(), gap) ?? false;
	}

	/** The read a widening makes of a gap, as much as one read of the file hands back; null where it reads nothing. */
	readOf(gap: ContextGap, widening: Widening): GapRead | null {
		return readOf(gap, widening, this.#review.limits.max_window_lines);
	}

	/** Read lines into a gap. */
	async read(read: GapRead): Promise<void> {
		await this.#revealed()?.reveal(this.path(), read);
	}

	/** Where the lines read in around the hunks are kept; null for a piece, which has nowhere to keep any. */
	#revealed(): RevealedContext | null {
		const extent = this.#source.extent();
		return extent.kind === 'whole' ? extent.revealed : null;
	}

	/** The file as it is drawn: with the lines revealed around its hunks, where they may be. */
	#shown(): DiffFile {
		const file = this.#source.file();
		const revealed = this.#revealed();
		return revealed ? withRevealed(file, revealed.forFile(file.path)) : file;
	}

	/** The gap below the last hunk as drawn, as far as a read has said how long the file is. */
	#gapAtTheEnd(): ContextGap | null {
		const last = this.#shownFile.hunks.at(-1);
		if (last === undefined) return null;
		return gapBelow(last, this.#revealed()?.forFile(this.path()).length ?? null);
	}
}
