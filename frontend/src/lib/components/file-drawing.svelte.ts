/**
 * A file made ready to draw, in whichever layout: its lines, commenting on
 * them, and reading in what the diff left out around its hunks — a file of
 * the diff, a piece cut out of one, which has nothing around it to read, or
 * a file read whole, which has nothing around it at all.
 *
 * Made once by whoever draws the file and handed to the layout, so both
 * layouts lay out the same lines, and switching between them prepares
 * nothing again.
 *
 * What the lines will take up is counted here too, from the same rules,
 * before any of them is drawn: their section holds that room until they are
 * built, so what lies below stays where it is as they are.
 */

import { type Numbering, STORY_PIECES_NUMBERING } from '$lib/anchors/numbering';
import { type DrawnFile, LineCommenting } from '$lib/components/line-commenting.svelte';
import { LineNaming } from '$lib/components/line-naming';
import type { LineArrivedAt } from '$lib/dom/arrived-line.svelte';
import type { FileSections } from '$lib/dom/file-sections';
import { DrawnName } from '$lib/review/drawn-name';
import type { NameLookup } from '$lib/review/name-lookup.svelte';
import type { RevealedContext } from '$lib/review/revealed-context.svelte';
import type { Review } from '$lib/review/review.svelte';
import { type FailureFound, NO_FAILURES } from '$lib/review/checks.svelte';
import type { DiffLayout, DiffLine, FileToDraw, LinePlace } from '$lib/types';
import { type DrawnHunk, type DrawnLine, drawnHunks } from '$lib/utils/drawn-file';
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
export function linesView(layout: DiffLayout, file: FileToDraw): 'split' | 'raw' {
	return layout === 'split' && file.hunks.length > 0 ? 'split' : 'raw';
}

/** The name gone to on a line of a file arrived at; null where the reader was taken to the line alone, or to none. */
function nameArrivedAt(sections: FileSections, path: string, arrived: LineArrivedAt | null): DrawnName | null {
	if (arrived === null || arrived.name === null) return null;
	return new DrawnName(sections, path, arrived.line, arrived.name);
}

/** A file of the diff on screen, drawn as the change made to it, with what the diff left out around its hunks. */
interface OfTheDiff {
	kind: 'of-the-diff';
	/** Whose numbers its lines carry, as the diff on screen was taken: see `DrawnFile`. */
	numbering: Numbering;
	/** Where the lines read in around its hunks are kept. */
	revealed: RevealedContext;
}

/** What a piece of a file is cut out to show: the lines a step of a story tells, or what no step tells of the file. */
export type PieceShows = 'a-step' | 'what-no-step-tells';

/**
 * A piece of a file, cut out of the review's own diff for a story, its
 * lines numbered as `STORY_PIECES_NUMBERING` says. What lies around it is
 * the rest of its file, which it does not read in.
 */
interface Piece {
	kind: 'piece';
	shows: PieceShows;
}

// What a piece says of the lines between two of its hunks, which it does not
// draw, of one line and of several. Between two hunks of a step lie lines the
// change kept. Between two runs no step tells may lie lines a step does tell,
// changed ones: they are not shown here, and nothing more is known of them.
const SAID_OF_A_GAP: Record<PieceShows, CountedWords> = {
	'a-step': { one: 'unchanged line', many: 'unchanged lines' },
	'what-no-step-tells': { one: 'line not shown here', many: 'lines not shown here' }
};

/**
 * A file read from its first line to its last, as it stands: nothing lies
 * around it to read in or to say, and no line of it is a change.
 */
interface EveryLine {
	kind: 'every-line';
}

/** What of a file a drawing is of: a file of the diff, a piece cut out of one, or a file read whole. */
export type Extent = OfTheDiff | Piece | EveryLine;

/** A file read whole, as every drawing of one is. */
export const EVERY_LINE: Extent = { kind: 'every-line' };

/** What a drawing of one extent is, whatever file it draws. */
interface DrawnAs {
	/** Whether it shows a change: two columns of numbers, a sign and a tint to each line, and what changed inside a replaced line marked. */
	showsChange: boolean;
	/** Whether it is of its file whole, which every thread of the file hangs in, rather than a piece of it. */
	ofItsFileWhole: boolean;
	/** Which gaps around and between its hunks it says. */
	saysGap: (gap: ContextGap) => boolean;
}

// What a drawing of each extent is. A file of the diff says every gap, which may be read in; a piece those between
// its own hunks, the rest of its file being none of it. A file read whole is the file itself: it changes nothing,
// and has no gap to say
const DRAWN_AS: Record<Extent['kind'], DrawnAs> = {
	'of-the-diff': { showsChange: true, ofItsFileWhole: true, saysGap: () => true },
	piece: { showsChange: true, ofItsFileWhole: false, saysGap: (gap) => gap.above !== null && gap.below !== null },
	'every-line': { showsChange: false, ofItsFileWhole: true, saysGap: () => false }
};

/** Whether a drawing of this extent shows a change. */
export function showsAChange(extent: Extent): boolean {
	return DRAWN_AS[extent.kind].showsChange;
}

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

/** Where the lines read in around a file's hunks are kept; null where nothing around them is read in. */
function revealedIn(extent: Extent): RevealedContext | null {
	return extent.kind === 'of-the-diff' ? extent.revealed : null;
}

/** A file as it is drawn: with the lines revealed around its hunks, where they may be. */
function shownFile(file: FileToDraw, extent: Extent): FileToDraw {
	const revealed = revealedIn(extent);
	return revealed ? withRevealed(file, revealed.forFile(file.path)) : file;
}

/**
 * The gap below the last hunk of a file as drawn, as far as a read has said
 * how long the file is, where the drawing draws it.
 */
function gapAtTheEnd(shown: FileToDraw, extent: Extent): ContextGap | null {
	const last = shown.hunks.at(-1);
	if (last === undefined) return null;
	const end = gapBelow(last, revealedIn(extent)?.forFile(shown.path).length ?? null);
	return end !== null && drawsGap(extent, end) ? end : null;
}

/**
 * Whether a gap is drawn: where it is the drawing's to say, while it hides
 * lines or may — below the last hunk, how many is not known until a read
 * finds out.
 */
function drawsGap(extent: Extent, gap: ContextGap): boolean {
	return DRAWN_AS[extent.kind].saysGap(gap) && hiddenIn(gap) !== 0;
}

/**
 * What a file's lines take up drawn in a view, counted without drawing
 * them, as `RawView`, `SplitView` and `HunkGap` draw them: the rows of each
 * hunk under the bar for what was left out above it, headed by the hunk's
 * header, and below the last hunk a bar headed by nothing.
 */
export function roomOf(file: FileToDraw, extent: Extent, view: FileView): LinesRoom {
	const shown = shownFile(file, extent);
	const { hunks } = shown;
	const barred = hunks.filter((hunk, index) => drawsGap(extent, gapAbove(hunk, hunks[index - 1])));
	// Below the last hunk, one bar more where that is drawn
	const barsBelow = gapAtTheEnd(shown, extent) === null ? 0 : 1;
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
	/** The section it is drawn in, by the key its view knows it by. */
	section: () => string;
	file: () => FileToDraw;
	/** What it is highlighted as, if anything. */
	language: () => string | null;
	/** How much of the file is drawn. */
	extent: () => Extent;
}

export class FileDrawing implements DrawnFile {
	readonly commenting: LineCommenting;
	/** Asking where a name in its lines is defined and used, where the review offers it. */
	readonly naming: LineNaming | null;
	readonly #review: Review;
	readonly #source: DrawingSource;
	readonly #shownFile: FileToDraw;
	readonly #hunks: DrawnHunk[];
	readonly #end: ContextGap | null;
	// Where the checks failed in the file, by the line of it as it stands: asked of every line drawn
	readonly #failuresByLine: ReadonlyMap<number, readonly FailureFound[]>;
	// The line the page took the reader to in its section, while the keyboard stays on it: asked of every line drawn
	readonly #arrived: LineArrivedAt | null;
	// The name gone to on it, found in the line as it is drawn while the line is lit
	readonly #arrivedName: DrawnName | null;

	/**
	 * @param review the review it is drawn in
	 * @param names the lookup of the area it is drawn in, where the review offers one
	 * @param source what it is drawn from
	 */
	constructor(review: Review, names: NameLookup | null, source: DrawingSource) {
		this.#review = review;
		this.#source = source;
		// Lines revealed from the file sit inside the hunk beside which they were
		// read, so numbering, highlighting and anchoring need no special case
		this.#shownFile = $derived(shownFile(source.file(), source.extent()));
		// What changed inside a replaced line is marked where a change is shown, which replaces lines
		this.#hunks = $derived(drawnHunks(this.#shownFile, source.language(), showsAChange(source.extent())));
		this.#end = $derived(gapAtTheEnd(this.#shownFile, source.extent()));
		this.#failuresByLine = $derived(
			Map.groupBy(review.checks.failuresIn(source.file().path), ({ failure }) => failure.line)
		);
		this.#arrived = $derived(review.sections.arrived.lineIn(source.section()));
		this.#arrivedName = $derived(nameArrivedAt(review.sections, source.file().path, this.#arrived));
		this.commenting = new LineCommenting(review, this);
		this.naming = names === null ? null : new LineNaming(review, names, this, this.commenting);
	}

	/** Whether a line is the one the page took the reader to, lit while the keyboard stays on it. */
	arrivedAt(drawn: DrawnLine): boolean {
		return drawn.key === this.#arrived?.line;
	}

	/** The name gone to on the line arrived at, while the line is lit; null while none is. */
	get arrivedName(): DrawnName | null {
		return this.#arrivedName;
	}

	/**
	 * Where the checks failed on a line: a check runs on the file as it
	 * stands, its new side, whose numbers are the review's own in every
	 * drawing, a narrower base's and a story's pieces too.
	 */
	failuresUnder(place: LinePlace): readonly FailureFound[] {
		return place.side === 'new' ? (this.#failuresByLine.get(place.number) ?? NO_FAILURES) : NO_FAILURES;
	}

	path(): string {
		return this.#source.file().path;
	}

	hunks(): DrawnHunk[] {
		return this.#hunks;
	}

	/** Whether its lines are drawn as a change: see `DrawnAs`. */
	get showsChange(): boolean {
		return showsAChange(this.#source.extent());
	}

	/** A file read whole is the file of the take as it stands, numbered as the review numbers its new side. */
	numbering(): Numbering {
		const extent = this.#source.extent();
		switch (extent.kind) {
			case 'of-the-diff':
				return extent.numbering;
			case 'piece':
				return STORY_PIECES_NUMBERING;
			case 'every-line':
				return 'the-reviews';
		}
	}

	commentable(): boolean {
		return this.#source.file().commentable;
	}

	standsForItsFile(): boolean {
		return DRAWN_AS[this.#source.extent().kind].ofItsFileWhole && this.numbering() === 'the-reviews';
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

	/** The gap below the last hunk, where the drawing says the file may go on past it; null where it does not. */
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
