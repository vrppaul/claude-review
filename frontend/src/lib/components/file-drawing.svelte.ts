/**
 * A file made ready to draw, in whichever layout: its lines, commenting on
 * them, and reading in what the diff left out above its hunks.
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
import { type ContextGap, withRevealed } from '$lib/utils/expansions';

/** What a file is drawn from and by, read afresh each time it matters. */
export interface DrawingSource {
	file: () => DiffFile;
	/** What it is highlighted as, if anything. */
	language: () => string | null;
	/** Whether the removed lines on screen are the review's own: see `DrawnFile`. */
	reviewOwnsRemovedLines: () => boolean;
	/** Where lines read in above the hunks are kept; null where the gaps are said but not read into. */
	revealed: () => RevealedContext | null;
}

export class FileDrawing implements DrawnFile {
	readonly commenting: LineCommenting;
	readonly #source: DrawingSource;
	readonly #hunks: DrawnHunk[];

	constructor(review: Review, source: DrawingSource) {
		this.#source = source;
		// Lines revealed from the file sit inside the hunk above which they were
		// read, so numbering, highlighting and anchoring need no special case;
		// what changed inside a replaced line is marked in a diff, where lines are replaced
		this.#hunks = $derived(drawnHunks(this.#shown(), source.language(), review.mode === 'diff'));
		this.commenting = new LineCommenting(review, this);
	}

	path(): string {
		return this.#source.file().path;
	}

	hunks(): DrawnHunk[] {
		return this.#hunks;
	}

	reviewOwnsRemovedLines(): boolean {
		return this.#source.reviewOwnsRemovedLines();
	}

	/** Whether what the diff left out may be read in here, or only said. */
	get readsGaps(): boolean {
		return this.#source.revealed() !== null;
	}

	/** Whether the lines of a gap are on their way. */
	isReading(gap: ContextGap): boolean {
		return this.#source.revealed()?.isReading(this.path(), gap) ?? false;
	}

	/** Read in the next lines of a gap. */
	async read(gap: ContextGap): Promise<void> {
		await this.#source.revealed()?.reveal(this.path(), gap);
	}

	/** The file as it is drawn: with the lines revealed above its hunks, where they may be. */
	#shown(): DiffFile {
		const file = this.#source.file();
		const revealed = this.#source.revealed();
		return revealed ? withRevealed(file, revealed.forFile(file.path)) : file;
	}
}
