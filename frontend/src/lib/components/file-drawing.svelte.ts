/**
 * A file made ready to draw, in whichever layout: its lines, commenting on
 * them, and reading in what the diff left out around its hunks — the whole
 * of the file, or a piece cut out of it, which has nothing around it to read.
 *
 * Made once by whoever draws the file and handed to the layout, so both
 * layouts lay out the same lines, and switching between them prepares
 * nothing again.
 *
 * What the lines will take up is counted here too, from the same rules,
 * before any of them is drawn: their section holds that room until they are
 * built, so what lies below stays where it is as they are.
 */

import type { DiffNumbering, Numbering, StoryNumbering } from '$lib/anchors/numbering';
import { type DrawnFile, LineCommenting } from '$lib/components/line-commenting.svelte';
import type { RevealedContext } from '$lib/review/revealed-context.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { DiffFile, DiffLayout, DiffLine } from '$lib/types';
import { type DrawnHunk, drawnHunks } from '$lib/utils/drawn-file';
import {
	type ContextGap,
	gapAbove,
	gapBelow,
	type GapRead,
	hiddenIn,
	readOf,
	type Widening,
	withRevealed
} from '$lib/utils/expansions';
import { splitRowCount } from '$lib/utils/split-rows';
import type { CountedWords } from '$lib/utils/words';

/** How a file's lines are drawn: rendered, rendered beside their text, in two columns, or in one. */
export type FileView = 'preview' | 'side-by-side' | 'split' | 'raw';

/** How a change's lines are laid out as the reader chose: in two columns where there are lines to set side by side. */
export function linesView(layout: DiffLayout, file: DiffFile): 'split' | 'raw' {
	return layout === 'split' && file.hunks.length > 0 ? 'split' : 'raw';
}

/** A file drawn whole, as the diff on screen has it. */
interface WholeFile {
	kind: 'whole';
	/** Whose numbers its lines carry, as the diff on screen was taken: see `DrawnFile`. */
	numbering: DiffNumbering;
	/** Where the lines read in around its hunks are kept. */
	revealed: RevealedContext;
}

/** What a piece of a file is cut out to show: the lines a step of a story tells, or what no step tells of the file. */
export type PieceShows = 'a-step' | 'what-no-step-tells';

/**
 * A piece of a file, cut out of the review's own diff for a story. Its
 * lines are numbered as the take the story was told of, whatever base is
 * on screen, and what lies around it is the rest of its file, which it
 * does not read in.
 */
interface Piece {
	kind: 'piece';
	shows: PieceShows;
	/** Whose numbers its lines carry, as the story it is a piece of says. */
	numbering: StoryNumbering;
}

// What a piece says of the lines between two of its hunks, which it does not
// draw, of one line and of several. Between two hunks of a step lie lines the
// change kept. Between two runs no step tells may lie lines a step does tell,
// changed ones: they are not shown here, and nothing more is known of them.
const SAID_OF_A_GAP: Record<PieceShows, CountedWords> = {
	'a-step': { one: 'unchanged line', many: 'unchanged lines' },
	'what-no-step-tells': { one: 'line not shown here', many: 'lines not shown here' }
};

/** How much of a file a drawing is of: the whole of it, or a piece. */
export type Extent = WholeFile | Piece;

/**
 * What a file's lines take up on the page, counted from what is drawn of
 * them: the room their section holds until they are built. What hangs under
 * a line — a thread, a comment being written — and a line or a header that
 * wraps take more, and are not counted.
 */
export interface LinesRoom {
	/** Rows of code, as many as the layout lays the lines out in. */
	rows: number;
	/** Hunks, each drawn above a rule of its own. */
	hunks: number;
	/** Bars saying what the diff left out around the hunks. */
	gaps: number;
	/** Hunk headers: each heads the bar above its hunk, where that is drawn. */
	hunkHeaders: number;
}

/** A layout that draws a hunk's lines one to a row. */
function oneToARow(lines: readonly DiffLine[]): number {
	return lines.length;
}

// How many rows each way of drawing a file lays a hunk's lines out in. A rendered preview draws no
// rows, and what it draws instead cannot be counted before it is drawn: it is taken to be as tall as them
const ROWS_OF_A_HUNK: Record<FileView, (lines: readonly DiffLine[]) => number> = {
	preview: oneToARow,
	'side-by-side': oneToARow,
	split: splitRowCount,
	raw: oneToARow
};
// A file with no lines says why in their place, and is held this many rows for it
const ROWS_FOR_NO_LINES = 1;

/** Where the lines read in around a file's hunks are kept; null for a piece, which has nowhere to keep any. */
function revealedIn(extent: Extent): RevealedContext | null {
	return extent.kind === 'whole' ? extent.revealed : null;
}

/** A file as it is drawn: with the lines revealed around its hunks, where they may be. */
function shownFile(file: DiffFile, extent: Extent): DiffFile {
	const revealed = revealedIn(extent);
	return revealed ? withRevealed(file, revealed.forFile(file.path)) : file;
}

/** The gap below the last hunk of a file as drawn, as far as a read has said how long the file is. */
function gapAtTheEnd(shown: DiffFile, extent: Extent): ContextGap | null {
	const last = shown.hunks.at(-1);
	if (last === undefined) return null;
	return gapBelow(last, revealedIn(extent)?.forFile(shown.path).length ?? null);
}

/**
 * Whether a gap is drawn: where it is the drawing's to say, while it hides
 * lines or may — below the last hunk, how many is not known until a read
 * finds out. A piece says what it leaves out between its own hunks; what
 * lies above its first and below its last is the rest of the file, which it
 * does not draw.
 */
function drawsGap(extent: Extent, gap: ContextGap): boolean {
	const says = extent.kind === 'whole' || (gap.above !== null && gap.below !== null);
	return says && hiddenIn(gap) !== 0;
}

/**
 * What a file's lines take up drawn in a view, counted without drawing
 * them, as `RawView`, `SplitView` and `HunkGap` draw them: the rows of each
 * hunk under the bar for what was left out above it, headed by the hunk's
 * header, and below the last hunk a bar headed by nothing.
 */
export function roomOf(file: DiffFile, extent: Extent, view: FileView): LinesRoom {
	const shown = shownFile(file, extent);
	const { hunks } = shown;
	const barred = hunks.filter((hunk, index) => drawsGap(extent, gapAbove(hunk, hunks[index - 1])));
	// Below the last hunk, one bar more where that is drawn
	const end = gapAtTheEnd(shown, extent);
	const barsBelow = end !== null && drawsGap(extent, end) ? 1 : 0;
	const rows = hunks.reduce((counted, hunk) => counted + ROWS_OF_A_HUNK[view](hunk.lines), 0);
	return {
		rows: Math.max(rows, ROWS_FOR_NO_LINES),
		hunks: hunks.length,
		gaps: barred.length + barsBelow,
		hunkHeaders: barred.filter((hunk) => hunk.header !== '').length
	};
}

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
		this.#shownFile = $derived(shownFile(source.file(), source.extent()));
		// What changed inside a replaced line is marked in a diff, where lines are replaced
		this.#hunks = $derived(drawnHunks(this.#shownFile, source.language(), review.mode === 'diff'));
		this.#end = $derived(gapAtTheEnd(this.#shownFile, source.extent()));
		this.commenting = new LineCommenting(review, this);
	}

	path(): string {
		return this.#source.file().path;
	}

	hunks(): DrawnHunk[] {
		return this.#hunks;
	}

	numbering(): Numbering {
		return this.#source.extent().numbering;
	}

	commentable(): boolean {
		return this.#source.file().commentable;
	}

	standsForItsFile(): boolean {
		const extent = this.#source.extent();
		return extent.kind === 'whole' && extent.numbering === 'the-reviews';
	}

	/** Whether a gap is drawn here: see `drawsGap`. */
	draws(gap: ContextGap): boolean {
		return drawsGap(this.#source.extent(), gap);
	}

	/**
	 * What is said of a gap where it is only said, of one line and of
	 * several: a piece reads nothing in. Null where what the diff left out
	 * may be read in instead.
	 */
	get saidOfAGap(): CountedWords | null {
		const extent = this.#source.extent();
		return extent.kind === 'piece' ? SAID_OF_A_GAP[extent.shows] : null;
	}

	/** The gap below the last hunk, where the file may go on past it; null where it cannot. */
	get end(): ContextGap | null {
		return this.#end;
	}

	/** Whether the lines of a gap are on their way. */
	isReading(gap: ContextGap): boolean {
		return revealedIn(this.#source.extent())?.isReading(this.path(), gap) ?? false;
	}

	/** The read a widening makes of a gap, as much as one read of the file hands back; null where it reads nothing. */
	readOf(gap: ContextGap, widening: Widening): GapRead | null {
		return readOf(gap, widening, this.#review.limits.max_window_lines);
	}

	/** Read lines into a gap. */
	async read(read: GapRead): Promise<void> {
		await revealedIn(this.#source.extent())?.reveal(this.path(), read);
	}
}
