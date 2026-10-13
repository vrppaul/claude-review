/**
 * Where each section that draws a file's lines, and each thread, sits in the
 * stream, which of them the reader is in, and bringing one into view.
 *
 * A section is known by a key whoever draws it gives: the files' own view
 * draws each file in one section and knows it by the file's path; a story
 * draws a file in as many sections as it has pieces of it, each under a key
 * of its own. So a section says both, its key and the file it draws lines
 * of, and a line of a file is looked for in every section that draws the file.
 *
 * The sidebar and the comment navigator move the reader by scrolling rather
 * than by swapping what is rendered, so find-in-page, text selection across
 * files and the browser's own history all keep working. Sections and threads
 * announce themselves here instead of being looked up on the page: nothing
 * depends on an id or a test id staying as it is, and no path ends up in a
 * query string.
 */

import { Announced, type Announcement } from '$lib/dom/announced';
import { firstInDocument } from '$lib/dom/document-order';
import type { Jumps } from '$lib/dom/jump';
import { focusWhatRemains } from '$lib/dom/keyboard';
import { scrollMotion } from '$lib/dom/motion';
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
// The class that draws the mark on a section somebody else pointed at
const MARKED_CLASS = 'cr-marked';
// How long a section or a thread asked for before it was drawn is waited
// for: a view brought on screen draws its sections, and a file is built or
// unfolded, within a frame or two, and what is never drawn — hidden by a
// narrower base, or outdated — must not pull the screen to it later
const AWAIT_DRAWING_FOR = 2000;

/** A thread asked for before it was drawn, and until when it is waited for. */
interface AwaitedThread {
	threadId: string;
	until: number;
}

/** A section as it announced itself: what it is known by and where it is, and the file it draws lines of. */
interface Section extends Announcement {
	path: string;
}

/** A section asked for before it was drawn: how the reader is taken to it once it is, and until when it is waited for. */
interface AwaitedSection {
	key: string;
	arrive: (section: Section) => void;
	until: number;
}

/** A section marked as the one pointed at, and the timer that takes the mark off. */
interface Mark {
	element: HTMLElement;
	timer: ReturnType<typeof setTimeout>;
}

export class FileSections {
	// Every section on the page, and which of them the reader is in, while the reading area is watched
	readonly #sections = new Announced<Section>();
	readonly #threads = new Map<string, HTMLElement>();
	// A thread asked for before it was drawn, and until when it is waited
	// for: brought into view once it is drawn, if that is soon
	#awaitedThread: AwaitedThread | null = null;
	// A section asked for before it was drawn — the view that draws it was
	// only just brought on screen — and until when it is waited for
	#awaitedSection: AwaitedSection | null = null;
	// What is marked, so a second showing can take the mark off the first
	// rather than leave it lit, and so the first one's timer cannot put it out
	#marked: Mark | null = null;
	// Where the page is taking the reader: one jump at a time, shared with
	// whatever else takes them somewhere, so an earlier jump neither pulls
	// them back nor marks its section once another was asked for
	readonly #jumps: Jumps;

	/** @param jumps where the page is taking the reader, one place at a time */
	constructor(jumps: Jumps) {
		this.#jumps = jumps;
	}

	/**
	 * The section the reader is in, by its key: the one at the top of the
	 * reading area, while the reading area is watched.
	 */
	get sectionInView(): string | null {
		return this.#sections.beingRead?.key ?? null;
	}

	/** The file the reader is in: the one that section draws lines of. */
	get fileInView(): string | null {
		return this.#sections.beingRead?.path ?? null;
	}

	/**
	 * Say where a section is: the key whoever draws it knows it by, and the
	 * file it draws lines of. Returns how to take it back.
	 */
	register(key: string, path: string, element: HTMLElement): () => void {
		const section = { key, path, element };
		const takeBack = this.#sections.add(section);
		const awaited = this.#awaitedSection;
		if (awaited?.key === key && performance.now() <= awaited.until) {
			this.#awaitedSection = null;
			awaited.arrive(section);
		}
		return takeBack;
	}

	/** Say where a thread is drawn; returns how to take it back. */
	registerThread(threadId: string, element: HTMLElement): () => void {
		this.#threads.set(threadId, element);
		const awaited = this.#awaitedThread;
		if (awaited?.threadId === threadId && performance.now() <= awaited.until) {
			this.#stopWaiting();
			this.#arriveAtThread(element);
		}
		return () => this.#unregisterThread(threadId, element);
	}

	/**
	 * Follow which section the reader is in as they scroll an area, so the
	 * sidebar can follow the scroll instead of driving it. Sections drawn
	 * later are watched as they arrive. Returns how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		return this.#sections.watch(root);
	}

	/** Where the reader is reading in an area: the first line still showing at its top, in the section being read. */
	readingPlace(root: HTMLElement): ReadingPlace | null {
		const section = this.#sections.beingRead;
		return section === null ? null : readingPlaceIn(section.key, section.element, root);
	}

	/** Put the reader back where they were reading, as near as what is drawn now allows; nowhere, if the section left. */
	returnTo(root: HTMLElement, place: ReadingPlace): void {
		const section = this.#sections.get(place.section);
		if (section) bringBack(place, section.element, root);
	}

	/** The section the reader is in, by its key: the one a line of which has the focus, if one has, or else the one in view. */
	current(): string | null {
		return this.#current()?.key ?? null;
	}

	/** The file of the section the reader is in. */
	currentFile(): string | null {
		return this.#current()?.path ?? null;
	}

	/**
	 * Take the reader to a section: its head to the top, and the section the
	 * one being read. One not drawn yet is gone to once it is, if that is soon.
	 */
	scrollTo(key: string): void {
		this.#stopWaiting();
		this.#onceDrawn(key, (section) => this.#scrollToDrawn(section));
	}

	/**
	 * Bring a section into view and mark it once it gets there.
	 *
	 * Somebody else moved this screen, so the section has to say "here" when
	 * it arrives: a page that has jumped somewhere without a word leaves the
	 * reader working out what they are looking at. The mark waits for the
	 * scroll to stop — across sixty files a smooth scroll outlasts the mark
	 * itself, and the reader would arrive to a file that had already finished
	 * saying so. A section not drawn yet is shown once it is, if that is soon.
	 */
	show(key: string): void {
		this.#stopWaiting();
		this.#onceDrawn(key, (section) => this.#showDrawn(section));
	}

	/**
	 * Bring a thread into view and put the keyboard on it, building or
	 * unfolding the section that draws it first if need be.
	 *
	 * A section's rows are only built once it has been near the viewport,
	 * and a folded file draws none, so a thread further down the review —
	 * restored from a draft, say — may have nothing drawn yet. Its section is
	 * brought into view instead, itself once it is drawn if its view has only
	 * just come on screen, and the thread follows the moment it is drawn, if
	 * that is soon.
	 */
	goToThread(threadId: string, sectionKey: string): void {
		const drawn = this.#threads.get(threadId);
		if (drawn) {
			this.#stopWaiting();
			this.#arriveAtThread(drawn);
			return;
		}
		this.scrollTo(sectionKey);
		this.#awaitedThread = { threadId, until: performance.now() + AWAIT_DRAWING_FOR };
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
	 * Put the keyboard on a line's number, by the file it is a line of and
	 * the key its place is known by, if what had it went: what remains where
	 * a comment was put away, a thread deleted, or hidden lines shown. Where
	 * the line is not drawn, the file's own toggle takes it; where the file
	 * is not drawn at all, the toggle of the first section, which its threads
	 * were drawn above. A section that folds nothing, a piece of a story, has
	 * no toggle to take it, and the keyboard is left where it is.
	 */
	keyboardToLine(path: string, lineKey: string): void {
		focusWhatRemains(() => this.lineOrFile(path, lineKey));
	}

	/**
	 * A line's number, in whichever section draws that line of its file, by
	 * the key its place is known by; or the toggle that stands for it where
	 * it is not drawn: that of the first section on the page to draw the
	 * file, or of the first section of all where none draws it. Null where
	 * that section has no toggle.
	 */
	lineOrFile(path: string, lineKey: string): HTMLElement | null {
		const ofTheFile = this.#sections.all.filter((section) => section.path === path).map((section) => section.element);
		if (ofTheFile.length === 0) return toggleOf(firstInDocument(this.#elements()));
		const line = ofTheFile
			.map((element) => element.querySelector<HTMLElement>(`[data-place="${lineKey}"]`))
			.find((found) => found !== null);
		return line ?? toggleOf(firstInDocument(ofTheFile));
	}

	/** The reader is being taken somewhere now: whatever was asked for before, and is not drawn yet, is waited for no longer. */
	#stopWaiting(): void {
		this.#awaitedThread = null;
		this.#awaitedSection = null;
	}

	/** Take the reader to a section as `arrive` does: now if it is drawn, or once it is, if that is soon. */
	#onceDrawn(key: string, arrive: (section: Section) => void): void {
		const section = this.#sections.get(key);
		if (section) arrive(section);
		else this.#awaitedSection = { key, arrive, until: performance.now() + AWAIT_DRAWING_FOR };
	}

	/**
	 * Bring a section that is drawn to the top at once: it is the one being
	 * read from now on, whatever the band says while it is on its way.
	 */
	#scrollToDrawn({ element }: Section): void {
		this.#jumps.land(this.#sections.band, element, 'instant');
	}

	/** Bring a section that is drawn to the top, as the one being read from now on, and mark it once it has come to rest. */
	#showDrawn({ element }: Section): void {
		this.#unmark();
		this.#jumps.land(this.#sections.band, element, scrollMotion(), () => this.#mark(element));
	}

	/**
	 * Take the reader to a thread, to the middle of its scrolling area —
	 * smoothly, unless they asked for less motion — and put the keyboard on
	 * it: the reader is there now, and the next key — a line down, the next
	 * file, marking it viewed — acts from there rather than from where the
	 * keyboard was before. The scroll is under way, so taking the keyboard
	 * does not move the screen again.
	 */
	#arriveAtThread(thread: HTMLElement): void {
		this.#jumps.to(thread, 'center', scrollMotion());
		thread.focus({ preventScroll: true });
	}

	/** Where every section is, in the order they announced themselves. */
	#elements(): HTMLElement[] {
		return this.#sections.all.map((section) => section.element);
	}

	/** The section the reader is in: the one holding the focus, if one does, or else the one being read. */
	#current(): Section | null {
		return this.#focused() ?? this.#sections.beingRead;
	}

	/** The section holding the focus, if any does. */
	#focused(): Section | null {
		const focus = document.activeElement;
		if (focus === null) return null;
		for (const section of this.#sections.all) {
			if (section.element.contains(focus)) return section;
		}
		return null;
	}

	#unregisterThread(threadId: string, element: HTMLElement): void {
		if (this.#threads.get(threadId) === element) this.#threads.delete(threadId);
	}

	#mark(element: HTMLElement): void {
		// The class draws the mark; the attribute says it is there to whatever
		// reads the page rather than its styles
		element.classList.add(MARKED_CLASS);
		element.dataset.marked = '';
		this.#marked = {
			element,
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

/** The toggle that folds a file's section: what stands for the file where nothing in it is drawn to stand for; null where the section folds nothing. */
function toggleOf(section: HTMLElement | null): HTMLElement | null {
	return section?.querySelector<HTMLElement>(`[data-role="${FOLD_TOGGLE_ROLE}"]`) ?? null;
}
