/**
 * The pieces of files a story draws, worked out once for the story held.
 *
 * A story draws a file in pieces — the lines of each step, and whatever of
 * the file no step tells — and whoever reads the review as its story asks
 * of them over and over: which piece shows this line, where is this file
 * first told, what comes after what, how much does the story change this
 * file. They are laid out once here, in the order the story draws them, and
 * found by file. They are the pieces of what the story lists of itself
 * (`story-contents.ts`), each under the key its section was listed by:
 * nothing here walks the story or names a section again.
 */

import type { StoryNumbering } from '$lib/anchors/numbering';
import { type DrawnRows, fileDraws } from '$lib/anchors/placement';
import type { FileLines } from '$lib/anchors/views';
import type { StoryContents } from '$lib/review/story-contents';
import type { DiffFile } from '$lib/types';
import { type FileStats, fileStats, totalOf } from '$lib/utils/file-stats';

/** A piece of a file a story draws, and what its section is known by. */
interface KeyedPiece {
	key: string;
	piece: DiffFile;
}

/** A piece as it stands among those the story draws: with its rows, and its place among the pieces. */
type DrawnPiece = KeyedPiece & DrawnRows;

// How much a story changes a file it draws nothing of
const NO_CHANGE = totalOf([]);

/** How much some pieces of a file change it together. */
function changeIn(pieces: readonly DrawnPiece[]): FileStats {
	return totalOf(pieces.map(({ piece }) => fileStats(piece)));
}

export class StoryPieces {
	readonly #inOrder: readonly DrawnPiece[];
	// The pieces of each file, in the order the story draws them: a line is looked for among its own file's alone
	readonly #byFile: ReadonlyMap<string, readonly DrawnPiece[]>;
	// How much the pieces of each file change it together, counted once
	readonly #changeByFile: ReadonlyMap<string, FileStats>;

	/** @param keyed the pieces in the order the story draws them, each with what its section is known by */
	constructor(keyed: readonly KeyedPiece[]) {
		this.#inOrder = keyed.map(({ key, piece }, place) => ({
			key,
			piece,
			place,
			rows: piece.hunks.flatMap((hunk) => hunk.lines)
		}));
		this.#byFile = Map.groupBy(this.#inOrder, ({ piece }) => piece.path);
		this.#changeByFile = new Map(
			[...this.#byFile].map(([path, pieces]): [string, FileStats] => [path, changeIn(pieces)])
		);
	}

	/** What each piece's section is known by, in the order the story draws them. */
	get keys(): string[] {
		return this.#inOrder.map(({ key }) => key);
	}

	/** The piece that draws a thread on these lines, numbered as the story's lines are; null where none does. */
	drawing(lines: FileLines, numbering: StoryNumbering): DrawnPiece | null {
		return this.ofFile(lines.file).find(({ piece }) => fileDraws(piece, lines, numbering)) ?? null;
	}

	/** The first piece of a file the story draws: where the file is first told; null where it draws none of it. */
	firstOf(path: string): DrawnPiece | null {
		return this.ofFile(path).at(0) ?? null;
	}

	/** The pieces of one file, in the order the story draws them: none of a file it draws nothing of. */
	ofFile(path: string): readonly DrawnPiece[] {
		return this.#byFile.get(path) ?? [];
	}

	/**
	 * How much the whole story changes a file: every piece it draws of it, a
	 * step's in any chapter or what no step tells. That is the file's whole
	 * change: the review refuses a line told twice, and what no step tells
	 * is drawn as left out. The diff on screen cannot be asked instead: it
	 * may be narrowed, or another take.
	 */
	changeOf(path: string): FileStats {
		return this.#changeByFile.get(path) ?? NO_CHANGE;
	}
}

/**
 * The pieces of what a story lists of itself, in the order it draws them:
 * every step that shows code as its chapter lists it, then what the story
 * leaves out; each under the key the listing knows its section by.
 */
export function piecesOf(contents: StoryContents): StoryPieces {
	const steps = contents.chapters.flatMap((chapter) =>
		chapter.steps.flatMap(({ section, shown }) => (shown === null ? [] : [{ key: section, piece: shown.piece }]))
	);
	const leftOut = contents.leftOut.map(({ section, told }) => ({ key: section, piece: told.piece }));
	return new StoryPieces([...steps, ...leftOut]);
}
