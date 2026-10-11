/**
 * Where each file and each thread sits in the stream, which file the reader
 * is in, and bringing one into view.
 *
 * The sidebar and the comment navigator move the reader by scrolling rather
 * than by swapping what is rendered, so find-in-page, text selection across
 * files and the browser's own history all keep working. Sections and threads
 * announce themselves here instead of being looked up on the page: nothing
 * depends on an id or a test id staying as it is, and no path ends up in a
 * query string.
 */

import { ReadingBand } from '$lib/dom/reading-band.svelte';

// Long enough to find what was pointed at, short enough not to become part
// of how the file looks
const MARKED_FOR = 2000;
// A smooth scroll that never ends — a scroll container that cannot reach the
// file, a tab put in the background mid-flight — must not swallow the mark
const SETTLE_WITHIN = 2000;
// How many frames in a row an element has to stay put to count as arrived
const STILL_FRAMES = 2;
// The class that draws the mark on a section somebody else pointed at
const MARKED_CLASS = 'cr-marked';
// How long a thread asked for before it was drawn is waited for: its file
// is built or unfolded within a frame or two, and one never drawn — hidden
// by a narrower base, or outdated — must not pull the screen to it later
const AWAIT_THREAD_FOR = 2000;

/** A thread asked for before it was drawn, and until when it is waited for. */
interface AwaitedThread {
	threadId: string;
	until: number;
}

/** A section marked as the one pointed at, and the timer that takes the mark off. */
interface Mark {
	element: HTMLElement;
	timer: ReturnType<typeof setTimeout>;
}

/**
 * Call back once an element has stopped moving.
 *
 * Where the element actually is, rather than which element is doing the
 * scrolling: a section sits inside whatever container the layout gives it,
 * and asking the element itself works wherever it ends up.
 */
class SettleWatch {
	readonly #element: HTMLElement;
	readonly #then: () => void;
	readonly #startedAt = performance.now();
	#previousTop = Number.NaN;
	#stillFor = 0;

	constructor(element: HTMLElement, then: () => void) {
		this.#element = element;
		this.#then = then;
	}

	/** Start looking, once a frame, until the element is still. */
	start(): void {
		requestAnimationFrame(() => this.#look());
	}

	#look(): void {
		const top = this.#element.getBoundingClientRect().top;
		this.#stillFor = top === this.#previousTop ? this.#stillFor + 1 : 0;
		this.#previousTop = top;

		const settled = this.#stillFor >= STILL_FRAMES;
		if (settled || performance.now() - this.#startedAt > SETTLE_WITHIN) {
			this.#then();
			return;
		}
		requestAnimationFrame(() => this.#look());
	}
}

export class FileSections {
	readonly #sections = new Map<string, HTMLElement>();
	// Which file each section stands for, so the section being read names its file
	readonly #paths = new Map<Element, string>();
	readonly #threads = new Map<string, HTMLElement>();
	// A thread asked for before it was drawn, and until when it is waited
	// for: brought into view once it is drawn, if that is soon
	#awaitedThread: AwaitedThread | null = null;
	// Which section the reader is in, while the reading area is watched
	readonly #band = new ReadingBand();
	// What is marked, so a second showing can take the mark off the first
	// rather than leave it lit, and so the first one's timer cannot put it out
	#marked: Mark | null = null;
	// Which showing is the current one: an earlier scroll may still be
	// settling when another arrives, and only the last one asked for is worth
	// marking
	#showing = 0;

	/**
	 * The file the reader is in: the one whose header is pinned at the top of
	 * the reading area, while the reading area is watched.
	 */
	get fileInView(): string | null {
		const earliest = this.#band.earliest;
		return earliest === null ? null : (this.#paths.get(earliest) ?? null);
	}

	/** Say where a file's section is; returns how to take it back. */
	register(path: string, element: HTMLElement): () => void {
		this.#sections.set(path, element);
		this.#paths.set(element, path);
		this.#band.add(element);
		return () => this.#unregister(path, element);
	}

	/** Say where a thread is drawn; returns how to take it back. */
	registerThread(threadId: string, element: HTMLElement): () => void {
		this.#threads.set(threadId, element);
		const awaited = this.#awaitedThread;
		if (awaited?.threadId === threadId && performance.now() <= awaited.until) {
			this.#awaitedThread = null;
			bringToCentre(element);
		}
		return () => this.#unregisterThread(threadId, element);
	}

	/**
	 * Follow which file the reader is in as they scroll an area, so the
	 * sidebar can follow the scroll instead of driving it. Files drawn later
	 * are watched as they arrive. Returns how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		return this.#band.watch(root, this.#sections.values());
	}

	/** The file whose section holds the focus, if any does. */
	focused(): string | null {
		const focus = document.activeElement;
		if (focus === null) return null;
		for (const [path, element] of this.#sections) {
			if (element.contains(focus)) return path;
		}
		return null;
	}

	scrollToFile(path: string): void {
		// Going anywhere else is no longer waiting for a thread
		this.#awaitedThread = null;
		this.#sections.get(path)?.scrollIntoView({ block: 'start' });
	}

	/**
	 * Bring a file into view and mark it once it gets there.
	 *
	 * Somebody else moved this screen, so the file has to say "here" when it
	 * arrives: a page that has jumped somewhere without a word leaves the
	 * reader working out what they are looking at. The mark waits for the
	 * scroll to stop — across sixty files a smooth scroll outlasts the mark
	 * itself, and the reader would arrive to a file that had already finished
	 * saying so.
	 */
	showFile(path: string): void {
		const section = this.#sections.get(path);
		if (!section) return;

		const showing = ++this.#showing;
		this.#awaitedThread = null;
		this.#unmark();
		section.scrollIntoView({ behavior: 'smooth', block: 'start' });
		new SettleWatch(section, () => this.#markIfStillShown(section, showing)).start();
	}

	/**
	 * Bring a thread into view, building or unfolding its file first if need be.
	 *
	 * A file's rows are only built once it has been near the viewport, and a
	 * folded file draws none, so a thread further down the review — restored
	 * from a draft, say — may have nothing drawn yet. Its file is brought into
	 * view instead, and the thread follows the moment it is drawn, however
	 * long that takes.
	 */
	scrollToThread(threadId: string, file: string): void {
		const drawn = this.#threads.get(threadId);
		if (drawn) {
			this.#awaitedThread = null;
			bringToCentre(drawn);
			return;
		}
		this.scrollToFile(file);
		this.#awaitedThread = { threadId, until: performance.now() + AWAIT_THREAD_FOR };
	}

	#unregister(path: string, element: HTMLElement): void {
		this.#band.remove(element);
		this.#paths.delete(element);
		if (this.#sections.get(path) === element) this.#sections.delete(path);
	}

	#unregisterThread(threadId: string, element: HTMLElement): void {
		if (this.#threads.get(threadId) === element) this.#threads.delete(threadId);
	}

	/** Mark a file the reader was brought to, unless another showing has come since. */
	#markIfStillShown(section: HTMLElement, showing: number): void {
		if (showing === this.#showing) this.#mark(section);
	}

	#mark(section: HTMLElement): void {
		// The class draws the mark; the attribute says it is there to whatever
		// reads the page rather than its styles
		section.classList.add(MARKED_CLASS);
		section.dataset.marked = '';
		this.#marked = {
			element: section,
			timer: setTimeout(() => this.#unmark(), MARKED_FOR)
		};
	}

	#unmark(): void {
		if (!this.#marked) return;
		clearTimeout(this.#marked.timer);
		this.#marked.element.classList.remove(MARKED_CLASS);
		delete this.#marked.element.dataset.marked;
		this.#marked = null;
	}
}

/** Scroll smoothly until an element stands in the middle of its scrolling area. */
function bringToCentre(element: HTMLElement): void {
	element.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
