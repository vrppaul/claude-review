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

/** What one read of the file came to: the file, or why it could not be read. */
type ReadOutcome = { kind: 'read'; file: FileToDraw } | { kind: 'failed'; why: string };

/** How the latest read of the file stands: on its way, read, or failed, and why. */
type LatestRead = { kind: 'reading' } | { kind: 'read' } | { kind: 'failed'; why: string };

/** The file read alone: what of it is drawn, and how its latest read, in one take, stands. */
interface HeldFile {
	path: string;
	/**
	 * The file as the last read that arrived has it, drawn while a later read
	 * of it is on its way, so reading it anew never takes its lines off the
	 * page; none until a read arrives, and none once one fails.
	 */
	drawn: FileToDraw | null;
	/** The take the latest read was asked in: another numbers the lines anew, so the file is read again for it. */
	take: number;
	latest: LatestRead;
}

// The latest read on its way, and arrived
const READING: LatestRead = { kind: 'reading' };
const READ: LatestRead = { kind: 'read' };

/** A file of the take as a section of lines draws it: its every line a line of its new side, one hunk. */
function asDrawn({ path, hunk, commentable }: FileOfTakeResponse): FileToDraw {
	return { path, hunks: [hunk], unshown: null, old_mode: null, new_mode: null, commentable };
}

/** Read a file of the take on screen, and say what that came to. */
async function outcomeOfReading(path: string): Promise<ReadOutcome> {
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
	// Which file is read alone, what of it is drawn, and how its latest read stands; none until the reader opens one
	#held = $state.raw<HeldFile | null>(null);
	// Settled once the read last asked for is, for whoever waits to go to a place in the file
	#settled: Promise<void> = Promise.resolve();

	/**
	 * @param diff the review's own diff, which the file is not in, and the take the file is read in
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

	/** The file as drawn: as its last read had it; null while none has arrived, or once one failed. */
	get file(): FileToDraw | null {
		return this.#held?.drawn ?? null;
	}

	/** Why the latest read of the file failed; null while none has. */
	get failure(): string | null {
		const latest = this.#held?.latest;
		return latest?.kind === 'failed' ? latest.why : null;
	}

	/**
	 * Read a file alone, in the take on screen, and settle once it is read:
	 * at once where it is read in that take already, or on its way; anew
	 * where it is another file, another take, or a read that failed. The file
	 * read anew stays drawn as it was until the new read arrives.
	 */
	open(path: string): Promise<void> {
		const take = this.#diff.takeOnScreen;
		const held = this.#held;
		if (held?.path === path && held.take === take && held.latest.kind !== 'failed') return this.#settled;
		const drawn = held?.path === path ? held.drawn : null;
		const asked: HeldFile = { path, drawn, take, latest: READING };
		this.#held = asked;
		this.#settled = this.#read(asked);
		return this.#settled;
	}

	/** Its lines, while drawn, which take comments; and the threads of the files, which n and p walk from here. */
	drawn(): Drawn {
		return { lines: this.file !== null, threads: this.threadsInOrder().length > 0 };
	}

	/** Its one section, while its lines are drawn. */
	sectionKeys(): string[] {
		const file = this.file;
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

	/** The file read from is opened alone again, and the reader put back once it is read, or says why it is not. */
	async returnTo(place: ReadingPlace): Promise<boolean> {
		// What a view of files whole knows a section by is its file's path
		await this.open(place.within);
		this.#sections.goBackTo(place);
		return true;
	}

	/**
	 * Read the file asked for, and hold what that came to while it is still
	 * the read last asked for: the file drawn as read, or no lines and why.
	 */
	async #read(asked: HeldFile): Promise<void> {
		const outcome = await outcomeOfReading(asked.path);
		if (this.#held !== asked) return;
		this.#held =
			outcome.kind === 'read'
				? { ...asked, drawn: outcome.file, latest: READ }
				: { ...asked, drawn: null, latest: outcome };
	}
}
