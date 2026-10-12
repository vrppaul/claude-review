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
 * so do ] and [ from section to section, and a file the agent names. What is
 * walked, and where a thread or a file is drawn, is asked of the view the
 * review is read in (`ReadingView`); what that view does not draw is gone to
 * in the one that draws everything, which is brought on screen for it. The
 * page itself is moved by `FileSections`. j and k move the keyboard line by line
 * (`dom/keyboard.ts`), and have no place among the threads to keep.
 */

import { anchorLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import type { ReadingView } from '$lib/review/reading-view';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

/** The views the review is read in, as moving the reader needs them. */
export interface ViewsOnScreen {
	/** The view the review is read in now. */
	readonly onScreen: ReadingView;
	/**
	 * Bring on screen the view that draws every thread and file the review
	 * holds, and hand it over. It need not be drawn yet: the page waits for
	 * a section asked for before it is.
	 */
	showEverything: () => Promise<ReadingView>;
}

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
	readonly #sections: FileSections;
	// The views the review is read in: what is walked, and where a thread or a file is drawn, is theirs to say
	readonly #views: ViewsOnScreen;
	// The thread the reader was last brought to, by whichever control, and the
	// one a step goes on from. Kept by id, with the threads as they stood: a
	// place in a list that changes would become another thread's, and a thread
	// removed leaves its neighbours to go on to.
	#at: ReaderAt | null = null;

	constructor(threads: Threads, sections: FileSections, views: ViewsOnScreen) {
		this.#threads = threads;
		this.#sections = sections;
		this.#views = views;
	}

	/** Step to the next or previous thread in the view on screen, and bring it into view. */
	step(direction: 1 | -1): void {
		const next = steppedTo(this.#views.onScreen.threadsInOrder(), this.#at, direction);
		if (next) this.reveal(next);
	}

	/**
	 * Bring a thread into view with the keyboard on it, and go on from it the
	 * next time the reader steps. Whatever folds its lines away is opened
	 * first, and the thread is gone to once it is drawn. A thread the view on
	 * screen does not draw is gone to in the view that draws them all, which
	 * comes on screen for it: the reader asked for the thread.
	 */
	reveal(thread: Thread): void {
		const onScreen = this.#views.onScreen;
		if (onScreen.sectionOf(anchorLines(thread.anchor)) !== null) this.#revealIn(onScreen, thread);
		else void this.#views.showEverything().then((drawingAll) => this.#revealIn(drawingAll, thread));
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
	 * Step to the next or previous section from the one the reader is in — by
	 * focus if a line in it has the focus, by scroll if not — and bring it into
	 * view; from nowhere, the first or the last.
	 */
	stepSection(direction: 1 | -1): void {
		const keys = this.#views.onScreen.sectionKeys();
		const here = this.#sections.current();
		const from = here === null ? -1 : keys.indexOf(here);
		const first = direction === 1 ? 0 : keys.length - 1;
		const to = from === -1 ? first : Math.min(keys.length - 1, Math.max(0, from + direction));
		const target = keys[to];
		if (target !== undefined) this.#sections.scrollTo(target);
	}

	/**
	 * Bring a file somebody named into view — the agent, in what it said or
	 * showed — and mark it once it gets there. A file the view on screen
	 * draws none of is shown in the view that draws every file the review
	 * holds, which comes on screen for it; one that view does not draw
	 * either is shown nowhere.
	 */
	showFile(path: string): void {
		const section = this.#views.onScreen.sectionOfFile(path);
		if (section !== null) this.#sections.show(section);
		else void this.#views.showEverything().then((drawingAll) => this.#showIn(drawingAll, path));
	}

	/** Go to a thread in a view, if the view draws it. */
	#revealIn(view: ReadingView, thread: Thread): void {
		const lines = anchorLines(thread.anchor);
		const section = view.sectionOf(lines);
		if (section === null) return;
		this.#at = { thread: thread.id, among: view.threadsInOrder() };
		view.unfold(lines);
		this.#sections.goToThread(thread.id, section);
	}

	/** Show a file in a view, if the view draws any of it. */
	#showIn(view: ReadingView, path: string): void {
		const section = view.sectionOfFile(path);
		if (section !== null) this.#sections.show(section);
	}
}
