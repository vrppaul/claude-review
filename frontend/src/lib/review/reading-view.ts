/**
 * A way the review is read on screen: which sections it draws, in what
 * order, and which of them draws a given line or file.
 *
 * Threads, keys and whatever takes the reader somewhere are the same however
 * the review is read; what differs is what is on the page. Each way of
 * reading answers for that here, so moving the reader never asks which one
 * is on screen — and another way of reading the same change is another
 * answer to these questions, not a branch in whoever asks them.
 */

import { inDiffOrder, isDrawn } from '$lib/anchors/placement';
import type { FileLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingPlace } from '$lib/dom/reading-place';
import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { LinePlace, Thread } from '$lib/types';
import { namesTheFileAsItStands, placeOfKey } from '$lib/utils/line-places';
import { fileName } from '$lib/utils/paths';

/**
 * What a view draws of the review as it stands, in the two things a key
 * acts on. A key that acts on what is not drawn does nothing, and is
 * neither answered nor listed: each asks of the one it acts on, so a view
 * that draws them another way is no change to any key.
 */
export interface Drawn {
	/** Whether it draws lines of the review's files, which take comments. */
	lines: boolean;
	/** Whether it draws threads: under lines that take comments, or with the lines they hung on gone from what is read. */
	threads: boolean;
}

/** What a view draws while it has nothing of the review to draw. */
export const NOTHING_DRAWN: Drawn = { lines: false, threads: false };

/** What a view draws of the review's lines: they take comments, and carry the threads on them. */
export const LINES_WITH_THEIR_THREADS: Drawn = { lines: true, threads: true };

export interface ReadingView {
	/** Which way of reading it is: the name the reader chooses it by, and the one its own keys and parts of the page are listed under. */
	readonly name: ReadingViewName;
	/** What it draws of the review as it stands. */
	drawn: () => Drawn;
	/** The sections it draws, by their keys, in the order it draws them: what ] and [ walk. */
	sectionKeys: () => string[];
	/** The threads it draws, in the order they stand in it: what n and p walk. */
	threadsInOrder: () => Thread[];
	/** The section a thread on these lines is drawn in, by its key; null where the view draws no such thread. */
	sectionOf: (lines: FileLines) => string | null;
	/** The section the reader is taken to for a file, by its key; null where the view draws none of the file. */
	sectionOfFile: (path: string) => string | null;
	/** Bring out lines the view has folded away, so what hangs on them can be drawn. */
	unfold: (lines: FileLines) => void;
	/**
	 * Bring a line of a file as it stands into what the view draws, and hand
	 * back the section it is drawn in, by its key; null where the view
	 * cannot draw it.
	 */
	drawLine: (path: string, line: number) => Promise<string | null>;
	/** Where the reader reads in it, and what to call that place; null while nothing of it is being read. */
	placeRead: () => PlaceRead | null;
	/**
	 * Put the reader back at a place read in it, as they saw it, once the
	 * place is drawn: its file unfolded, its line read in. False where the
	 * view cannot draw the place now, and the reader is not moved.
	 */
	returnTo: (place: ReadingPlace) => Promise<boolean>;
}

/** Where the reader reads in a view, and what the way back there calls it. */
export interface PlaceRead {
	place: ReadingPlace;
	/** As short as the reader knows it: a file's name and the line, `routes.ts:33`, or a chapter's title. */
	called: string;
	/** In full, on the pointer: `src/http/routes.ts:33`. */
	calledInFull: string;
}

/** A place in a section of lines, called by its file and the line read from; null for a section not drawn. */
export function placeInLines(sections: FileSections, place: ReadingPlace): PlaceRead | null {
	const path = sections.fileOf(place.within);
	if (path === null) return null;
	const line = place.line === null ? null : placeOfKey(place.line);
	return { place, called: lineCalled(fileName(path), line), calledInFull: lineCalled(path, line) };
}

/** A file and the line read from in it, as the reader knows them: `routes.ts:33`; the file alone where there is none. */
function lineCalled(file: string, line: LinePlace | null): string {
	return line === null ? file : `${file}:${line.number}`;
}

/**
 * The threads on lines that a view draws none of. They are still in the
 * review and still go out with the round: whoever shows the view counts
 * them and offers the way to where they are drawn.
 */
export function threadsNotDrawnIn(view: ReadingView, threads: Threads): Thread[] {
	return threads.onLines.filter(({ lines }) => view.sectionOf(lines) === null).map(({ thread }) => thread);
}

/** What the files' own view knows a file's section by: its path, since it draws each file once. */
export function fileSectionKey(path: string): string {
	return path;
}

/** The review read file by file: every file of the diff on screen in a section of its own, in the diff's order. */
export class FilesReading implements ReadingView {
	readonly name = 'files';
	readonly #diff: ReviewDiff;
	readonly #threads: Threads;
	readonly #reading: ReadingProgress;
	// The sections the files are drawn in, which say where the reader reads and take them back there
	readonly #sections: FileSections;
	// The most lines one read of a file hands back
	readonly #longestRead: number;

	constructor(
		diff: ReviewDiff,
		threads: Threads,
		reading: ReadingProgress,
		sections: FileSections,
		longestRead: number
	) {
		this.#diff = diff;
		this.#threads = threads;
		this.#reading = reading;
		this.#sections = sections;
		this.#longestRead = longestRead;
	}

	/**
	 * While the diff on screen holds a file, lines that take a comment
	 * whatever base they are read against: on the side that is the review's
	 * own. Over a diff of no file, the threads on files it held, which are
	 * drawn above it; and with none of those, nothing.
	 */
	drawn(): Drawn {
		if (this.#diff.files.length > 0) return LINES_WITH_THEIR_THREADS;
		return { ...NOTHING_DRAWN, threads: this.threadsInOrder().length > 0 };
	}

	sectionKeys(): string[] {
		return this.#diff.files.map((file) => fileSectionKey(file.path));
	}

	/**
	 * Down the diff, file by file and row by row; those on files it no longer
	 * holds first, as they are drawn above it. Under a narrower base, only
	 * the threads that base draws.
	 */
	threadsInOrder(): Thread[] {
		const drawn = this.#threads.onLines.filter(({ lines }) => this.sectionOf(lines) !== null);
		return inDiffOrder(drawn, this.#diff.files);
	}

	/**
	 * Read against the review's own base, every thread is drawn somewhere
	 * here: under its line, at the head of its file where the line is not
	 * shown, or above the files where the diff no longer holds the file.
	 * Each is found from the file's section. A narrower base draws only the
	 * threads on lines it shows whose numbers are the review's own; the rest
	 * are drawn once the whole review is put back.
	 */
	sectionOf(lines: FileLines): string | null {
		const leftOut = this.#diff.narrowed && !isDrawn(lines, this.#diff.files, this.#diff.numbering);
		return leftOut ? null : fileSectionKey(lines.file);
	}

	sectionOfFile(path: string): string | null {
		return this.#diff.files.some((file) => file.path === path) ? fileSectionKey(path) : null;
	}

	/** A folded file draws no line, and no thread: it is opened. */
	unfold(lines: FileLines): void {
		this.#reading.unfold(lines.file);
	}

	/**
	 * Any line of a file the diff on screen holds, whatever base it is read
	 * against, as the file as it stands is the review's own side: its file
	 * unfolded, and what the diff left out around it read in.
	 */
	async drawLine(path: string, line: number): Promise<string | null> {
		const file = this.#diff.files.find((held) => held.path === path);
		if (file === undefined) return null;
		this.#reading.unfold(path);
		await this.#diff.revealed.revealLine(file, line, this.#longestRead);
		return fileSectionKey(path);
	}

	placeRead(): PlaceRead | null {
		const place = this.#sections.readingPlace(namesTheFileAsItStands);
		return place === null ? null : placeInLines(this.#sections, place);
	}

	/**
	 * A line read from is drawn first: its file unfolded, and a line of the
	 * file as it stands read in where the diff on screen leaves it out. The
	 * top of a file is gone back to as the reader left the file, folded or
	 * not. A file the diff on screen holds none of is not drawn.
	 */
	async returnTo(place: ReadingPlace): Promise<boolean> {
		// What the files' own view knows a section by is its file's path
		const path = place.within;
		if (this.sectionOfFile(path) === null) return false;
		const line = place.line === null ? null : placeOfKey(place.line);
		if (line?.side === 'new') await this.drawLine(path, line.number);
		else if (line !== null) this.#reading.unfold(path);
		this.#sections.goBackTo(place);
		return true;
	}
}
