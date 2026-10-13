/**
 * The pieces of files a story draws, worked out once for the story held.
 *
 * A story draws a file in pieces — the lines of each step, and whatever of
 * the file no step tells — and whoever reads the review as its story asks
 * of them over and over: which piece shows this line, where is this file
 * first told, what comes after what. They are laid out once here, in the
 * order the story draws them, and found by file.
 *
 * A section of the page is known by what it draws, never by where the story
 * happens to put it: a step by its file and the first line it tells, which
 * no two steps share since the review refuses a story that tells a line
 * twice; what is left out of a file by that file, which is left out once.
 * So a section is the same section when the story is told again in another
 * order.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { type DrawnRows, fileDraws } from '$lib/anchors/placement';
import type { FileLines } from '$lib/anchors/views';
import type { DiffFile, LeftOut, ToldStep, ToldStory } from '$lib/types';

// What the key of a step's section begins with, and the key of a section of what is left out
const STEP_SECTION = 'step';
const LEFT_OUT_SECTION = 'left-out';
// What stands between the parts of a section's key
const KEY_SEPARATOR = ':';

/** What a step's section is known by: its file, and the first of the lines it tells. */
export function stepSectionKey(step: ToldStep): string {
	return [STEP_SECTION, step.file, step.lines.first].join(KEY_SEPARATOR);
}

/** What the section of what a story leaves out of a file is known by: the file. */
export function leftOutSectionKey(left: LeftOut): string {
	return [LEFT_OUT_SECTION, left.piece.path].join(KEY_SEPARATOR);
}

/** A piece of a file a story draws, and what its section is known by. */
interface KeyedPiece {
	key: string;
	piece: DiffFile;
}

/** A piece as it stands among those the story draws: with its rows, and its place among the pieces. */
type DrawnPiece = KeyedPiece & DrawnRows;

export class StoryPieces {
	readonly #inOrder: readonly DrawnPiece[];
	// The pieces of each file, in the order the story draws them: a line is looked for among its own file's alone
	readonly #byFile: ReadonlyMap<string, readonly DrawnPiece[]>;

	/** @param keyed the pieces in the order the story draws them, each with what its section is known by */
	constructor(keyed: readonly KeyedPiece[]) {
		this.#inOrder = keyed.map(({ key, piece }, place) => ({
			key,
			piece,
			place,
			rows: piece.hunks.flatMap((hunk) => hunk.lines)
		}));
		this.#byFile = Map.groupBy(this.#inOrder, ({ piece }) => piece.path);
	}

	/** What each piece's section is known by, in the order the story draws them. */
	get keys(): string[] {
		return this.#inOrder.map(({ key }) => key);
	}

	/** The piece that draws a thread on these lines, numbered as the story's lines are; null where none does. */
	drawing(lines: FileLines, numbering: StoryNumbering): DrawnPiece | null {
		return this.#ofFile(lines.file).find(({ piece }) => fileDraws(piece, lines, numbering)) ?? null;
	}

	/** The first piece of a file the story draws: where the file is first told; null where it draws none of it. */
	firstOf(path: string): DrawnPiece | null {
		return this.#ofFile(path).at(0) ?? null;
	}

	/** The pieces of one file, in the order the story draws them. */
	#ofFile(path: string): readonly DrawnPiece[] {
		return this.#byFile.get(path) ?? [];
	}
}

/** The pieces a story draws, in the order it draws them: its steps as it tells them, then what it leaves out. */
export function piecesOf(story: ToldStory): StoryPieces {
	const steps = story.chapters.flatMap((chapter) =>
		chapter.steps.map((step) => ({ key: stepSectionKey(step), piece: step.piece }))
	);
	const leftOut = story.left_out.map((left) => ({ key: leftOutSectionKey(left), piece: left.piece }));
	return new StoryPieces([...steps, ...leftOut]);
}

/** The pieces of no story: while none is held, nothing is drawn. */
export const NO_PIECES = new StoryPieces([]);
