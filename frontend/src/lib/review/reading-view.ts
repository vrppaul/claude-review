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

import { tick } from 'svelte';
import type { FileLines, ThreadLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { KeyboardOnReturn, ReadingPlace } from '$lib/dom/reading-place';
import type { ReadingChoice } from '$lib/reader/page-layout.svelte';
import { drawnByTheChange, threadsInFilesOrder } from '$lib/review/files-way';
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

/** Every view the review is read in: one the reader chose, or a file the change did not touch, read alone. */
export type ReadingViewName = ReadingChoice | 'file-alone';

export interface ReadingView {
	/** Which view it is: the name its own keys and parts of the page are listed under. */
	readonly name: ReadingViewName;
	/** The way of reading the reader chose that it is one of: what the header's switch shows while it is on screen. */
	readonly readAs: ReadingChoice;
	/** What it draws of the review as it stands. */
	drawn: () => Drawn;
	/** The sections it draws, by their keys, in the order it draws them: what ] and [ walk. */
	sectionKeys: () => string[];
	/** The threads of its way of reading, in the order they stand in it: what n and p walk. */
	threadsInOrder: () => Thread[];
	/** The section a thread on these lines is drawn in, by its key; null where the view draws no such thread. */
	sectionOf: (lines: ThreadLines) => string | null;
	/** The section the reader is taken to for a file, by its key; null where the view draws none of the file. */
	sectionOfFile: (path: string) => string | null;
	/** Bring out lines the view has folded away, so what hangs on them can be drawn. */
	unfold: (lines: FileLines) => void;
	/**
	 * Bring a line of a file into what the view draws, and hand back the
	 * section it is drawn in, by its key; null where the view cannot draw it.
	 */
	drawLine: (path: string, line: LinePlace) => Promise<string | null>;
	/** Where the reader reads in the section named, or else the one being read, and what to call it; null for none. */
	placeRead: (section?: string) => PlaceRead | null;
	/**
	 * Put the reader back at a place read in it, as they saw it, once the
	 * place is drawn: its file unfolded, its line read in. False where the
	 * view cannot draw the place now, and the reader is not moved.
	 */
	returnTo: (place: ReadingPlace, keyboard: KeyboardOnReturn) => Promise<boolean>;
}

/** Where the reader reads in a view, and what the way back there calls it. */
export interface PlaceRead {
	place: ReadingPlace;
	/** As short as the reader knows it: a file's name and the line, `routes.ts:33`, or a chapter's title. */
	called: string;
	/** In full, on the pointer: `src/http/routes.ts:33`. */
	calledInFull: string;
}

/** Where the reader was as they left a view: the view they read in, and where in it. */
export interface PlaceLeft extends PlaceRead {
	view: ReadingViewName;
}

/** Where the reader reads in a view, in the section named or the one being read, as the place they leave it at. */
export function placeLeftIn(view: ReadingView, section?: string): PlaceLeft | null {
	const read = view.placeRead(section);
	return read === null ? null : { ...read, view: view.name };
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

/** What a view that draws each file whole, once, knows the file's section by: its path. */
export function fileSectionKey(path: string): string {
	return path;
}

/** The review read file by file: every file of the diff on screen in a section of its own, in the diff's order. */
export class FilesReading implements ReadingView {
	readonly name = 'files';
	readonly readAs = 'files';
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
	 * own. Over a diff of no file, the threads n and p walk, those above it
	 * and those on files read alone; and with none of those, nothing.
	 */
	drawn(): Drawn {
		if (this.#diff.files.length > 0) return LINES_WITH_THEIR_THREADS;
		return { ...NOTHING_DRAWN, threads: this.threadsInOrder().length > 0 };
	}

	sectionKeys(): string[] {
		return this.#diff.files.map((file) => fileSectionKey(file.path));
	}

	/** As the Files way of reading walks them (`threadsInFilesOrder`). */
	threadsInOrder(): Thread[] {
		return threadsInFilesOrder(this.#threads, this.#diff);
	}

	/**
	 * Each thread the change's files draw (`drawnByTheChange`) is found from
	 * its file's section: under its line, at the head of its file, or above
	 * the files, where its file is gone.
	 */
	sectionOf(lines: ThreadLines): string | null {
		return drawnByTheChange(lines, this.#diff) ? fileSectionKey(lines.file) : null;
	}

	sectionOfFile(path: string): string | null {
		return this.#diff.shows(path) ? fileSectionKey(path) : null;
	}

	/** A folded file draws no line, and no thread: it is opened. */
	unfold(lines: FileLines): void {
		this.#reading.unfold(lines.file);
	}

	/**
	 * Any line of a file the diff on screen holds: its file unfolded, and for
	 * a line of the file as it stands, whatever base it is read against,
	 * what the diff left out around it read in. A line of the old side is
	 * one the diff draws, as it removed it.
	 */
	async drawLine(path: string, line: LinePlace): Promise<string | null> {
		const file = this.#diff.files.find((held) => held.path === path);
		if (file === undefined) return null;
		this.#reading.unfold(path);
		if (line.side === 'new') await this.#diff.revealed.revealLine(file, line.number, this.#longestRead);
		return fileSectionKey(path);
	}

	placeRead(section?: string): PlaceRead | null {
		const place = this.#sections.readingPlace(namesTheFileAsItStands, section);
		return place === null ? null : placeInLines(this.#sections, place);
	}

	/**
	 * A line read from is drawn first: its file unfolded, and a line of the
	 * file as it stands read in where the diff on screen leaves it out. The
	 * top of a file is gone back to as the reader left the file, folded or
	 * not. A file the diff on screen holds none of is not drawn.
	 */
	async returnTo(place: ReadingPlace, keyboard: KeyboardOnReturn): Promise<boolean> {
		// What the files' own view knows a section by is its file's path
		if (this.sectionOfFile(place.within) === null) return false;
		await this.#drawPlace(place);
		this.#sections.goBackTo(place, keyboard);
		return true;
	}

	/**
	 * Take the reader over from a file read alone that the change now
	 * touches, as a new diff keeps them, which is no jump they asked for: on
	 * the line they read, drawn first, and the keyboard back on the line that
	 * held it, or on what stands for that line where it is not drawn. Called
	 * as these files come on screen, before the file read alone is gone.
	 */
	async takeOver(place: ReadingPlace): Promise<void> {
		const keyboardOn = this.#sections.lineWithTheKeyboard();
		await this.#drawPlace(place);
		// The files come on screen, and the section is drawn, once what is pending is
		await tick();
		this.#sections.returnTo(place);
		if (keyboardOn !== null) this.#sections.keyboardBackTo(place.within, keyboardOn);
	}

	/** Draw a place read: its line read in where the diff on screen leaves it out, its file unfolded. */
	async #drawPlace(place: ReadingPlace): Promise<void> {
		const line = place.line === null ? null : placeOfKey(place.line);
		if (line?.side === 'new') await this.drawLine(place.within, line);
		else if (line !== null) this.#reading.unfold(place.within);
	}
}
