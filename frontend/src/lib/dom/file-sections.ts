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

import { focusWhatRemains } from '$lib/dom/keyboard';
import { ReadingBand } from '$lib/dom/reading-band.svelte';
import { bringBack, type ReadingPlace, readingPlaceIn } from '$lib/dom/reading-place';

/**
 * What every toggle that folds something carries — a thread, a file — so the
 * keyboard can be put back on the one drawn anew when what it folds changes
 * shape. A role of its own, as a line's number has one.
 */
export const FOLD_TOGGLE_ROLE = 'fold-toggle';

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
			arriveAt(element);
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

	/** Where the reader is reading in an area: the first line still showing at its top, in the file being read. */
	readingPlace(root: HTMLElement): ReadingPlace | null {
		const path = this.fileInView;
		const section = path === null ? undefined : this.#sections.get(path);
		return path === null || section === undefined ? null : readingPlaceIn(path, section, root);
	}

	/** Put the reader back where they were reading, as near as what is drawn now allows; nowhere, if the file left. */
	returnTo(root: HTMLElement, place: ReadingPlace): void {
		const section = this.#sections.get(place.path);
		if (section) bringBack(place, section, root);
	}

	/** The file the reader is in: the one a line of which has the focus, if one has, or else the one in view. */
	current(): string | null {
		return this.focused() ?? this.fileInView;
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

	/** Take the reader to a file: its header to the top, and the file the one being read. */
	scrollToFile(path: string): void {
		// Going anywhere else is no longer waiting for a thread
		this.#awaitedThread = null;
		const section = this.#sections.get(path);
		if (!section) return;
		this.#land(section);
		section.scrollIntoView({ block: 'start' });
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
		this.#band.land(section);
		section.scrollIntoView({ behavior: 'smooth', block: 'start' });
		new SettleWatch(section, () => this.#arrivedAtShown(section, showing)).start();
	}

	/**
	 * Bring a thread into view and put the keyboard on it, building or
	 * unfolding its file first if need be.
	 *
	 * A file's rows are only built once it has been near the viewport, and a
	 * folded file draws none, so a thread further down the review — restored
	 * from a draft, say — may have nothing drawn yet. Its file is brought into
	 * view instead, and the thread follows the moment it is drawn, however
	 * long that takes.
	 */
	goToThread(threadId: string, file: string): void {
		const drawn = this.#threads.get(threadId);
		if (drawn) {
			this.#awaitedThread = null;
			arriveAt(drawn);
			return;
		}
		this.scrollToFile(file);
		this.#awaitedThread = { threadId, until: performance.now() + AWAIT_THREAD_FOR };
	}

	/** Put the keyboard on a thread once it is drawn, if what had it went: the thread a comment became, or what remains of a change to it. */
	keyboardToThread(threadId: string): void {
		focusWhatRemains(() => this.#threads.get(threadId));
	}

	/** Put the keyboard on the toggle that folds a thread, as it is drawn now, if what had it went with the fold. */
	keyboardToThreadFold(threadId: string): void {
		focusWhatRemains(() =>
			this.#threads.get(threadId)?.querySelector<HTMLElement>(`[data-role="${FOLD_TOGGLE_ROLE}"]`)
		);
	}

	/**
	 * Put the keyboard on a line's number, by the key its place is known by,
	 * if what had it went: what remains where a comment was put away, a
	 * thread deleted, or hidden lines shown. Where the line is not drawn, the
	 * file's own toggle takes it.
	 */
	keyboardToLine(path: string, lineKey: string): void {
		focusWhatRemains(() => this.lineOrFile(path, lineKey));
	}

	/** A line's number in a file's section, by the key its place is known by, or the file's toggle where it is not drawn. */
	lineOrFile(path: string, lineKey: string): HTMLElement | null {
		const section = this.#sections.get(path);
		if (!section) return null;
		const line = section.querySelector<HTMLElement>(`[data-place="${lineKey}"]`);
		return line ?? section.querySelector<HTMLElement>(`[data-role="${FOLD_TOGGLE_ROLE}"]`);
	}

	#unregister(path: string, element: HTMLElement): void {
		this.#band.remove(element);
		this.#paths.delete(element);
		if (this.#sections.get(path) === element) this.#sections.delete(path);
	}

	#unregisterThread(threadId: string, element: HTMLElement): void {
		if (this.#threads.get(threadId) === element) this.#threads.delete(threadId);
	}

	/** The file being read from now on is the one a jump is taking the reader to, once it has come to rest. */
	#land(section: HTMLElement): void {
		this.#band.land(section);
		new SettleWatch(section, () => this.#band.settle(section)).start();
	}

	/** A file the reader was brought to has come to rest: mark it, unless another showing has come since. */
	#arrivedAtShown(section: HTMLElement, showing: number): void {
		this.#band.settle(section);
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

/**
 * Scroll smoothly until a thread stands in the middle of its scrolling area,
 * and put the keyboard on it: the reader is there now, and the next key — a
 * line down, the next file, marking it viewed — acts from there rather than
 * from where the keyboard was before. The scroll is under way, so taking the
 * keyboard does not move the screen again.
 */
function arriveAt(thread: HTMLElement): void {
	thread.scrollIntoView({ behavior: 'smooth', block: 'center' });
	thread.focus({ preventScroll: true });
}
