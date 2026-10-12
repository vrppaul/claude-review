/**
 * The review read as the story the agent told of it: every step a section of
 * its own, in the order the story tells them, then what no step tells.
 *
 * A story draws a file in pieces — a step's lines, and whatever of the file
 * no step tells — so a file may stand in several sections, and a line of it
 * in at most one: the review refuses a story that tells a line twice. A
 * thread on a line no piece shows is not drawn here at all; the files,
 * read against the review's own base, draw every thread. Nor is any thread drawn in a story told of
 * another take of the change than the page reads: its lines are numbered
 * as that take, and a thread hangs on a line of the take on screen.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { isDrawn, rowOf } from '$lib/anchors/placement';
import type { FileLines, ThreadOnLines } from '$lib/anchors/views';
import type { ReadingView } from '$lib/review/reading-view';
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { DiffFile, Thread, ToldStory } from '$lib/types';

/** A piece of a file as the story draws it, and what its section is known by. */
interface DrawnPiece {
	key: string;
	piece: DiffFile;
}

/** A thread as it stands in the story: the piece that draws it, by its place among the pieces, and the row it hangs under. */
interface Standing {
	thread: Thread;
	piecePlace: number;
	row: number;
}

/** What a step's section is known by: where the step stands in the story as it was told. */
export function stepSectionKey(chapterPlace: number, stepPlace: number): string {
	return `step:${chapterPlace}:${stepPlace}`;
}

/** What the section of what a story leaves out of one file is known by: its place among what was left out. */
export function leftOutSectionKey(place: number): string {
	return `left-out:${place}`;
}

/** Every piece a story draws, in the order it draws them: its steps as it tells them, then what it leaves out. */
function piecesOf(story: ToldStory): DrawnPiece[] {
	const steps = story.chapters.flatMap((chapter, chapterPlace) =>
		chapter.steps.map((step, stepPlace) => ({ key: stepSectionKey(chapterPlace, stepPlace), piece: step.piece }))
	);
	const leftOut = story.left_out.map((left, place) => ({ key: leftOutSectionKey(place), piece: left.piece }));
	return [...steps, ...leftOut];
}

/**
 * Whether a piece draws a thread on these lines: it is a piece of their
 * file, holds the line, and numbers it as the review does.
 */
function draws({ piece }: DrawnPiece, lines: FileLines, numbering: StoryNumbering): boolean {
	return isDrawn(lines, [piece], numbering);
}

/** Where a thread stands among the pieces, if one of them draws it. */
function standingOf(
	{ thread, lines }: ThreadOnLines,
	pieces: readonly DrawnPiece[],
	numbering: StoryNumbering
): Standing[] {
	const piecePlace = pieces.findIndex((drawn) => draws(drawn, lines, numbering));
	const drawn = pieces[piecePlace];
	if (drawn === undefined) return [];
	const rows = drawn.piece.hunks.flatMap((hunk) => hunk.lines);
	return [{ thread, piecePlace, row: rowOf(lines, rows) }];
}

export class StoryReading implements ReadingView {
	readonly name = 'story';
	readonly #story: ReviewStory;
	readonly #threads: Threads;

	constructor(story: ReviewStory, threads: Threads) {
		this.#story = story;
		this.#threads = threads;
	}

	sectionKeys(): string[] {
		return this.#pieces().map((drawn) => drawn.key);
	}

	/** Down the story, piece by piece and row by row: only the threads a piece draws. */
	threadsInOrder(): Thread[] {
		const pieces = this.#pieces();
		const numbering = this.#story.numbering;
		return this.#threads.onLines
			.flatMap((onLines) => standingOf(onLines, pieces, numbering))
			.sort((one, other) => one.piecePlace - other.piecePlace || one.row - other.row)
			.map(({ thread }) => thread);
	}

	sectionOf(lines: FileLines): string | null {
		const numbering = this.#story.numbering;
		return this.#pieces().find((drawn) => draws(drawn, lines, numbering))?.key ?? null;
	}

	/** The first piece of the file the story draws: where the file is first told. */
	sectionOfFile(path: string): string | null {
		return this.#pieces().find((drawn) => drawn.piece.path === path)?.key ?? null;
	}

	/** A story folds nothing away. */
	unfold(): void {
		// Nothing of a story is folded: every piece it draws is on the page
	}

	/** A story is not read file by file: it has no file to tick off or fold. */
	fileBeingRead(): null {
		return null;
	}

	/** The pieces the story held now draws; none while no story is held. */
	#pieces(): DrawnPiece[] {
		const held = this.#story.held;
		return held === null ? [] : piecesOf(held.story);
	}
}
