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
// The band across the top of the reading area a file is read in: a long
// file below the one whose header is pinned is in view too, but it is not
// the one being read
const READING_BAND = '0px 0px -85% 0px';

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
	// Which file each section stands for, for what an observer reports
	readonly #paths = new Map<Element, string>();
	readonly #threads = new Map<string, HTMLElement>();
	// A thread asked for before it was drawn: its file is being built, or
	// unfolded, and the thread is brought into view once it is drawn
	#awaitedThread: string | null = null;
	// Which files are in the reading band, while something is watching it
	#band: IntersectionObserver | null = null;
	readonly #inBand = new Set<string>();
	// What is marked, so a second showing can take the mark off the first
	// rather than leave it lit, and so the first one's timer cannot put it out
	#marked: Mark | null = null;
	// Which showing is the current one: an earlier scroll may still be
	// settling when another arrives, and only the last one asked for is worth
	// marking
	#showing = 0;

	/** Say where a file's section is; returns how to take it back. */
	register(path: string, element: HTMLElement): () => void {
		this.#sections.set(path, element);
		this.#paths.set(element, path);
		this.#band?.observe(element);
		return () => {
			this.#band?.unobserve(element);
			this.#paths.delete(element);
			if (this.#sections.get(path) !== element) return;
			this.#sections.delete(path);
			this.#inBand.delete(path);
		};
	}

	/** Say where a thread is drawn; returns how to take it back. */
	registerThread(threadId: string, element: HTMLElement): () => void {
		this.#threads.set(threadId, element);
		if (this.#awaitedThread === threadId) {
			this.#awaitedThread = null;
			bringToCentre(element);
		}
		return () => {
			if (this.#threads.get(threadId) === element) this.#threads.delete(threadId);
		};
	}

	/**
	 * Report which files are in the reading band of a scrolling area, so the
	 * sidebar can follow the scroll instead of driving it. Files drawn later
	 * are watched as they arrive. Returns how to stop.
	 */
	watchInView(root: HTMLElement, onChange: (inBand: ReadonlySet<string>) => void): () => void {
		const band = new IntersectionObserver((entries) => this.#crossed(entries, onChange), {
			root,
			rootMargin: READING_BAND,
			threshold: 0
		});
		this.#band = band;
		for (const element of this.#sections.values()) band.observe(element);
		return () => {
			band.disconnect();
			if (this.#band !== band) return;
			this.#band = null;
			this.#inBand.clear();
		};
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

		const mine = ++this.#showing;
		this.#unmark();
		section.scrollIntoView({ behavior: 'smooth', block: 'start' });
		new SettleWatch(section, () => {
			if (mine === this.#showing) this.#mark(section);
		}).start();
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
		this.#awaitedThread = threadId;
		this.scrollToFile(file);
	}

	#crossed(entries: IntersectionObserverEntry[], onChange: (inBand: ReadonlySet<string>) => void): void {
		for (const entry of entries) {
			const path = this.#paths.get(entry.target);
			if (path === undefined) continue;
			if (entry.isIntersecting) this.#inBand.add(path);
			else this.#inBand.delete(path);
		}
		onChange(this.#inBand);
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
