/**
 * A file of the take the change did not touch, read alone in place of the
 * change's files: whole, from its first line to its last, so scrolling
 * never leads into another file.
 *
 * The reader comes here to read what the change left — a use the agent
 * forgot — and comments on it as on any line. It is read as Files, the way
 * the reader chose, so n and p walk on from it through every thread of the
 * files. The file comes on screen at once and reads itself here: what the
 * take holds of it is read only once the reader opens it.
 */

import { readFileOfTake } from '$lib/api/review-api';
import type { ThreadLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingPlace } from '$lib/dom/reading-place';
import { threadsInFilesOrder, whereRead } from '$lib/review/files-way';
import { type Drawn, fileSectionKey, placeInLines, type PlaceRead, type ReadingView } from '$lib/review/reading-view';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { FileOfTakeResponse, FileToDraw, Thread } from '$lib/types';
import { messageOf } from '$lib/utils/errors';
import { namesTheFileAsItStands } from '$lib/utils/line-places';

/** What reading the file came to: on its way, the file, or why it could not be read. */
type FileAloneRead = { kind: 'reading' } | { kind: 'read'; file: FileToDraw } | { kind: 'failed'; why: string };

/**
 * The file read alone, and what reading it came to. A file the change does
 * not touch is the pinned base's own in every take, so it is read once, and
 * again only at Try again: never for a take.
 */
interface HeldRead {
	path: string;
	outcome: FileAloneRead;
}

// A read on its way
const READING: FileAloneRead = { kind: 'reading' };

/** A file of the take as a section of lines draws it: its every line a line of its new side, one hunk. */
function asDrawn({ path, hunk, commentable }: FileOfTakeResponse): FileToDraw {
	return { path, hunks: [hunk], unshown: null, old_mode: null, new_mode: null, commentable };
}

/** Read a file of the take on screen, and say what that came to. */
async function outcomeOfReading(path: string): Promise<FileAloneRead> {
	try {
		return { kind: 'read', file: asDrawn(await readFileOfTake(path)) };
	} catch (error) {
		return { kind: 'failed', why: messageOf(error) };
	}
}

export class FileAloneReading implements ReadingView {
	readonly name = 'file-alone';
	readonly readAs = 'files';
	readonly #diff: ReviewDiff;
	readonly #threads: Threads;
	// The section the file is drawn in, which says where the reader reads and takes them back there
	readonly #sections: FileSections;
	// Which file is read alone, and what reading it came to; none until the reader opens one
	#held = $state.raw<HeldRead | null>(null);
	// Settled once the read last asked for is, for whoever waits to go to a place in the file
	#settled: Promise<void> = Promise.resolve();

	/**
	 * @param diff the review's own diff, which the file is not in
	 * @param threads the threads, some on this file
	 * @param sections where the file's section announces itself
	 */
	constructor(diff: ReviewDiff, threads: Threads, sections: FileSections) {
		this.#diff = diff;
		this.#threads = threads;
		this.#sections = sections;
	}

	/** The file read alone, or read so last; null until the reader opens one. */
	get path(): string | null {
		return this.#held?.path ?? null;
	}

	/** What reading that file came to; null until the reader opens one. */
	get outcome(): FileAloneRead | null {
		return this.#held?.outcome ?? null;
	}

	/**
	 * Read a file alone, and settle once it is read: at once where it is read
	 * already, or on its way; anew where it is another file, or its read
	 * failed.
	 */
	open(path: string): Promise<void> {
		const held = this.#held;
		if (held?.path === path && held.outcome.kind !== 'failed') return this.#settled;
		const asked: HeldRead = { path, outcome: READING };
		this.#held = asked;
		this.#settled = this.#read(asked);
		return this.#settled;
	}

	/** Its lines, while drawn, which take comments; and the threads of the files, which n and p walk from here. */
	drawn(): Drawn {
		return { lines: this.#file() !== null, threads: this.threadsInOrder().length > 0 };
	}

	/** Its one section, while its lines are drawn. */
	sectionKeys(): string[] {
		const file = this.#file();
		return file === null ? [] : [fileSectionKey(file.path)];
	}

	/** As the Files way of reading walks them (`threadsInFilesOrder`). */
	threadsInOrder(): Thread[] {
		return threadsInFilesOrder(this.#threads, this.#diff);
	}

	/** Every thread read in this file: under its line, or at its head where its lines are not drawn. */
	sectionOf(lines: ThreadLines): string | null {
		return whereRead(lines, this.#diff) === 'in-its-file-alone' ? this.sectionOfFile(lines.file) : null;
	}

	sectionOfFile(path: string): string | null {
		return path === this.path ? fileSectionKey(path) : null;
	}

	/** Nothing of a file read alone is folded. */
	unfold(): void {
		// Every line of the file is drawn
	}

	/** Every line of the file is drawn. */
	drawLine(path: string): Promise<string | null> {
		return Promise.resolve(this.sectionOfFile(path));
	}

	placeRead(): PlaceRead | null {
		const place = this.#sections.readingPlace(namesTheFileAsItStands);
		return place === null ? null : placeInLines(this.#sections, place);
	}

	/**
	 * Open the file read from alone again, and put the reader back on the
	 * place once it is read. The view draws the file whatever the read came
	 * to, its failure said in place, so it can always draw the place.
	 */
	async returnTo(place: ReadingPlace): Promise<boolean> {
		// What a view of files whole knows a section by is its file's path
		await this.open(place.within);
		this.#sections.goBackTo(place);
		return true;
	}

	/** Read the file asked for, and hold what that came to while it is still the read last asked for. */
	async #read(asked: HeldRead): Promise<void> {
		const outcome = await outcomeOfReading(asked.path);
		if (this.#held === asked) this.#held = { ...asked, outcome };
	}

	/** The file as read; null while it is on its way, or once its read failed. */
	#file(): FileToDraw | null {
		const outcome = this.#held?.outcome;
		return outcome?.kind === 'read' ? outcome.file : null;
	}
}
