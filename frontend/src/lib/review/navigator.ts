/**
 * Moving the reader through the review: from thread to thread, whatever
 * each hangs on, and from file to file.
 *
 * Naming a thread is the anchor's business and touches nothing; bringing one
 * into view opens what hides it and moves the screen, so it lives here, with
 * the parts of the page it moves — and so does where the reader has got to
 * among the threads, which only moving changes. Every control that takes the
 * reader to a thread moves them through here — n and p, a, the header's
 * arrows, the replies, the finish pane, the panel's chips, the notices — and
 * so do ] and [ from file to file. A file named outright, by the tree or by
 * the agent, is brought into view by `FileSections` itself, and j and k move
 * the keyboard line by line (`dom/keyboard.ts`): neither has a place among
 * the threads to keep.
 */

import { anchorLines, type FileLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingProgress } from '$lib/review/reading-progress.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

/** Where the reader is among the threads: the one they were last brought to, among the threads as they stood then. */
interface ReaderAt {
	thread: string;
	among: readonly Thread[];
}

/**
 * The thread a step lands on: the next or the previous, round from the end
 * to the start. From a thread since removed, the nearest of its neighbours
 * that is still there, the way the step goes; from nowhere, the first going
 * on and the last going back.
 */
function steppedTo(threads: readonly Thread[], from: ReaderAt | null, direction: 1 | -1): Thread | undefined {
	const here = threads.findIndex((thread) => thread.id === from?.thread);
	if (here !== -1) return threads[(here + direction + threads.length) % threads.length];
	const neighbour = from ? nearestStillThere(threads, from, direction) : undefined;
	return neighbour ?? (direction === 1 ? threads.at(0) : threads.at(-1));
}

/** The nearest neighbour of a removed thread that is still there, the way a step goes, as the threads stood. */
function nearestStillThere(threads: readonly Thread[], from: ReaderAt, direction: 1 | -1): Thread | undefined {
	const stillThere = new Map(threads.map((thread) => [thread.id, thread]));
	const was = from.among.findIndex((thread) => thread.id === from.thread);
	const neighbour =
		direction === 1
			? from.among.slice(was + 1).find((thread) => stillThere.has(thread.id))
			: from.among.slice(0, Math.max(was, 0)).findLast((thread) => stillThere.has(thread.id));
	return neighbour && stillThere.get(neighbour.id);
}

export class Navigator {
	readonly #threads: Threads;
	readonly #reading: ReadingProgress;
	readonly #sections: FileSections;
	readonly #diff: ReviewDiff;
	// The thread the reader was last brought to, by whichever control, and the
	// one a step goes on from. Kept by id, with the threads as they stood: a
	// place in a list that changes would become another thread's, and a thread
	// removed leaves its neighbours to go on to.
	#at: ReaderAt | null = null;

	constructor(threads: Threads, reading: ReadingProgress, sections: FileSections, diff: ReviewDiff) {
		this.#threads = threads;
		this.#reading = reading;
		this.#sections = sections;
		this.#diff = diff;
	}

	/** Step to the next or previous thread, and bring it into view. */
	step(direction: 1 | -1): void {
		const next = steppedTo(this.#threads.all, this.#at, direction);
		if (next) this.reveal(next);
	}

	/** Bring a thread into view with the keyboard on it, and go on from it the next time the reader steps. */
	reveal(thread: Thread): void {
		this.#at = { thread: thread.id, among: this.#threads.all };
		this.#revealOnLines(thread.id, anchorLines(thread.anchor));
	}

	/** Bring a thread into view to read its answer, which reading it marks read. */
	readAnswer(thread: Thread): void {
		this.reveal(thread);
		this.#threads.reading.markRead(thread.id);
	}

	/** Go to the oldest thread carrying an answer nobody has looked at, if any does. */
	nextUnread(): void {
		const [oldest] = this.#threads.unread;
		if (oldest) this.readAnswer(oldest);
	}

	/**
	 * Step to the next or previous file from the one the reader is in — by
	 * focus if a line in it has the focus, by scroll if not — and bring it into
	 * view; from nowhere, the first or the last.
	 */
	stepFile(direction: 1 | -1): void {
		const files = this.#diff.files;
		const here = this.#sections.current();
		const from = files.findIndex((file) => file.path === here);
		const first = direction === 1 ? 0 : files.length - 1;
		const to = from === -1 ? first : Math.min(files.length - 1, Math.max(0, from + direction));
		const target = files[to];
		if (target) this.#sections.scrollToFile(target.path);
	}

	#revealOnLines(threadId: string, lines: FileLines): void {
		// A folded file has no thread on screen to move to, so it is opened
		// first; the thread is brought into view once it is drawn
		this.#reading.unfold(lines.file);
		this.#sections.goToThread(threadId, lines.file);
	}
}
