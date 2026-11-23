/**
 * Where each section that draws a file's lines, each thread, and what offers
 * each block of a story's words to be asked about sits in the stream, which
 * of them the reader is in, bringing one into view, and stepping the
 * keyboard through the lines they draw.
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

import { tick } from 'svelte';
import { Announced, type Announcement } from '$lib/dom/announced';
import { ArrivedLine, type LineArrivedAt } from '$lib/dom/arrived-line.svelte';
import { firstInDocument } from '$lib/dom/document-order';
import type { Jumps } from '$lib/dom/jump';
import { focusWhatRemains, moveByLine, seenWhole } from '$lib/dom/keyboard';
import { LineReadFrom } from '$lib/dom/line-read-from.svelte';
import {
	bringBack,
	goBackAmong,
	type KeyboardOnReturn,
	type ReadingPlace,
	readingPlaceIn
} from '$lib/dom/reading-place';

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
// How long a thread on lines asked for before it was drawn is waited for:
// the rows of its section are built once the reader comes near it, a frame
// or a few after the section is gone to, and one drawn much later must not
// pull the screen to it
const AWAIT_ROWS_FOR = 2000;

/** A thread on lines asked for before its rows were built, and until when it is waited for. */
interface AwaitedThread {
	threadId: string;
	until: number;
}

/** A section as it announced itself: what it is known by and where it is, and the file it draws lines of. */
interface Section extends Announcement {
	path: string;
}

/** A section marked as the one pointed at, and the timer that takes the mark off. */
interface Mark {
	element: HTMLElement;
	timer: ReturnType<typeof setTimeout>;
}

/** Lines the reader reads from, by the keys their places are known by, and the file they are of. */
interface LinesRead {
	path: string;
	lines: readonly string[];
}

/** Stop following the sections of an area and the line read from in it. */
function stopWatching(stopSections: () => void, stopLine: () => void): void {
	stopSections();
	stopLine();
}

export class FileSections {
	/** The line the reader was last taken to, lit while the keyboard stays on it. */
	readonly arrived = new ArrivedLine();
	// Every section on the page, and which of them the reader is in, while the reading area is watched
	readonly #sections = new Announced<Section>();
	// The line the reader reads from, and the section it is drawn in, as they scroll
	readonly #lineReadFrom = new LineReadFrom((element) => this.#sectionHolding(element));
	readonly #threads = new Map<string, HTMLElement>();
	// What offers each block of the story's words to be asked about, by what the block is known by
	readonly #blocks = new Map<string, HTMLElement>();
	// A thread on lines asked for before its rows were built, and until when
	// it is waited for: brought into view once it is drawn, if that is soon
	#awaitedThread: AwaitedThread | null = null;
	// How many times the reader has been taken somewhere: what was asked for
	// as its view came on screen is gone to once that view is drawn, unless
	// the reader was taken somewhere else meanwhile
	#taken = 0;
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

	/** The file a section draws lines of, by the section's key; null for a section not drawn. */
	fileOf(sectionKey: string): string | null {
		return this.#sections.get(sectionKey)?.path ?? null;
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
		return this.#sections.add({ key, path, element });
	}

	/** Say where a thread is drawn; returns how to take it back. */
	registerThread(threadId: string, element: HTMLElement): () => void {
		this.#threads.set(threadId, element);
		const awaited = this.#awaitedThread;
		if (awaited?.threadId === threadId && performance.now() <= awaited.until) {
			this.#beginTaking();
			this.#arriveAt(element);
		}
		return () => this.#unregisterThread(threadId, element);
	}

	/** Say what offers a block of the story's words to be asked about, by what the block is known by; returns how to take it back. */
	registerBlock(blockKey: string, asking: HTMLElement): () => void {
		this.#blocks.set(blockKey, asking);
		return () => this.#unregisterBlock(blockKey, asking);
	}

	/**
	 * Follow which section the reader is in, and the line they read from, as
	 * they scroll an area, so the sidebar can follow the scroll instead of
	 * driving it. Sections drawn later are watched as they arrive. Returns
	 * how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		const stopSections = this.#sections.watch(root);
		const stopLine = this.#lineReadFrom.watch(root);
		return () => stopWatching(stopSections, stopLine);
	}

	/**
	 * The lines the reader reads from and the file they are of: the line they were taken to while it is lit and
	 * they see it, else the line at the top of the area while it is of the file in view.
	 */
	get linesRead(): LinesRead | null {
		// Read first: whether the reader still sees the line they were taken to is looked at again as the top moves
		const read = this.#lineReadFrom.read;
		// A jump stands its line in the middle of the area, where the top is another line, or near a file's head the
		// file above: the reader reads from the line all the same, until they scroll it out of sight
		const arrived = this.arrived.lit;
		if (arrived !== null && this.seesLine(arrived.section, arrived.line)) {
			return this.#linesOf(arrived.section, [arrived.line]);
		}
		const atTheTop = read === null ? null : this.#linesOf(read.section, read.lines);
		// After a jump to a file the area cannot scroll up to, the line at the top is the file above's
		return atTheTop?.path === this.fileInView ? atTheTop : null;
	}

	/**
	 * Where the reader is reading in the section being read, while the
	 * reading area is watched, as `readingPlaceIn` reads it. None while no
	 * section is being read.
	 */
	readingPlace(standsAlike: (lineKey: string) => boolean): ReadingPlace | null {
		const section = this.#sections.beingRead;
		return section === null ? null : this.#placeReadIn(section, standsAlike);
	}

	/**
	 * Where the reader is reading in a section named by its key, read as in
	 * the section being read, wherever it stands in the area: a section the
	 * reader acted from, though another is at the top. None for a section
	 * not drawn, or while the reading area is not watched.
	 */
	readingPlaceInSection(sectionKey: string, standsAlike: (lineKey: string) => boolean): ReadingPlace | null {
		const section = this.#sections.get(sectionKey);
		return section === undefined ? null : this.#placeReadIn(section, standsAlike);
	}

	/** Whether the reader sees a line's number whole in a section now, by the key its place is known by. */
	seesLine(sectionKey: string, lineKey: string): boolean {
		const section = this.#sections.get(sectionKey);
		const area = this.#sections.area;
		const line = section === undefined ? null : lineIn(section.element, lineKey);
		return line !== null && area !== null && seenWhole(line, area);
	}

	/** Put the reader back where they were reading, as near as what is drawn now allows; nowhere, if the section left. */
	returnTo(place: ReadingPlace): void {
		const section = this.#sections.get(place.within);
		const area = this.#sections.area;
		if (section && area) bringBack(place, section.element, area);
	}

	/**
	 * Take the reader back to where they were reading, as they saw it, once
	 * the view that draws it is drawn: where the keyboard goes there, on the
	 * line they read from, or on the file's own toggle where they read from none.
	 */
	goBackTo(place: ReadingPlace, keyboard: KeyboardOnReturn): void {
		this.#onceDrawn(
			() => this.#sections.get(place.within),
			() => goBackAmong(this.#sections, this.#jumps, place, keyboard, keyboardToPlace)
		);
	}

	/** The section the reader is in, by its key: the one a line of which has the focus, if one has, or else the one in view. */
	current(): string | null {
		return this.#current()?.key ?? null;
	}

	/** The line whose number holds the keyboard, in any section, by the key its place is known by; null where none does. */
	lineWithTheKeyboard(): string | null {
		const focus = document.activeElement;
		if (!(focus instanceof HTMLElement) || this.#focused() === null) return null;
		return focus.dataset.place ?? null;
	}

	/**
	 * Put the keyboard on a line's number, by the file it is a line of and
	 * the key its place is known by, the screen left still: on what stands
	 * for the line where it is not drawn (`lineOrFile`).
	 */
	keyboardBackTo(path: string, lineKey: string): void {
		this.lineOrFile(path, lineKey)?.focus({ preventScroll: true });
	}

	/** The file of the section the reader is in. */
	currentFile(): string | null {
		return this.#current()?.path ?? null;
	}

	/**
	 * Move the keyboard a line down or up among the lines of the reading
	 * area: from the line that holds it to the next, and from outside the
	 * area to the line the reader reads from (`moveByLine`). Nowhere while
	 * no area is watched: every line is drawn in one.
	 */
	stepLine(step: 1 | -1): void {
		const area = this.#sections.area;
		if (area !== null) moveByLine(area, step);
	}

	/**
	 * Take the reader to a section: its head to the top, and the section the
	 * one being read. One not drawn yet is gone to once its view is drawn.
	 */
	scrollTo(key: string): void {
		this.#onceDrawn(
			() => this.#sections.get(key),
			(section) => this.#scrollToDrawn(section)
		);
	}

	/**
	 * Bring a section into view and mark it once it gets there.
	 *
	 * Somebody else moved this screen, so the section has to say "here" when
	 * it arrives: a page that has jumped somewhere without a word leaves the
	 * reader working out what they are looking at. The mark waits for the
	 * jump to come to rest, so it is drawn where the section is put right
	 * once the files around it are built. A section not drawn yet is shown
	 * once its view is drawn.
	 */
	show(key: string): void {
		this.#onceDrawn(
			() => this.#sections.get(key),
			(section) => this.#showDrawn(section)
		);
	}

	/**
	 * Bring a thread into view and put the keyboard on it, building or
	 * unfolding the section that draws it first if need be.
	 *
	 * A section's rows are only built once it has been near the viewport,
	 * and a folded file draws none, so a thread further down the review —
	 * restored from a draft, say — may have nothing drawn yet. Its section is
	 * brought into view instead, itself once its view is drawn if that has
	 * only just come on screen, and the thread follows the moment its rows
	 * are built, if that is soon.
	 */
	goToThread(threadId: string, sectionKey: string): void {
		if (!this.#threads.has(threadId)) this.scrollTo(sectionKey);
		this.#reachThread(threadId);
	}

	/**
	 * Take the reader to a line's number in a section, by the key its place
	 * is known by, to the middle of the reading area with the keyboard on it,
	 * the line lit and the name gone to on it marked while the keyboard stays
	 * there, once what is pending is drawn: lines just read in, a file
	 * unfolded, a view just come on screen. Rows not built yet are built as
	 * their section is brought into view, and the line is gone to once that
	 * comes to rest.
	 */
	goToLine(sectionKey: string, arrived: LineArrivedAt): void {
		const taking = this.#beginTaking();
		void tick().then(() => this.#reachLine(taking, sectionKey, arrived));
	}

	/**
	 * Bring a thread on the story's words into view and put the keyboard on
	 * it: now if it is drawn, or once the story is, if it has only just come
	 * on screen. The story draws its words whole as it is drawn: there is no
	 * section to build for one.
	 */
	goToStoryThread(threadId: string): void {
		this.#onceDrawn(
			() => this.#threads.get(threadId),
			(thread) => this.#arriveAt(thread)
		);
	}

	/** Put the keyboard on a thread once it is drawn, if what had it went: the thread a comment became, or what remains of a change to it. */
	keyboardToThread(threadId: string): void {
		focusWhatRemains(() => this.#threads.get(threadId));
	}

	/** Put the keyboard on what offers a block of the story to be asked about, if what had it went: a comment on the block put away, a thread on it deleted. */
	keyboardToBlock(blockKey: string): void {
		focusWhatRemains(() => this.#blocks.get(blockKey));
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
		const ofTheFile = this.#drawing(path);
		if (ofTheFile.length === 0) return toggleOf(firstInDocument(this.#elements()));
		return lineAmong(ofTheFile, lineKey) ?? toggleOf(firstInDocument(ofTheFile));
	}

	/**
	 * A line's number as it is drawn now, in whichever section draws that
	 * line of its file, by the key its place is known by; null where none
	 * draws it.
	 */
	line(path: string, lineKey: string): HTMLElement | null {
		return lineAmong(this.#drawing(path), lineKey);
	}

	/** Where the reader is reading in a section, as `readingPlaceIn` reads it; none while the area is not watched. */
	#placeReadIn(section: Section, standsAlike: (lineKey: string) => boolean): ReadingPlace | null {
		const area = this.#sections.area;
		return area === null ? null : readingPlaceIn(section.key, section.element, area, standsAlike);
	}

	/** The sections on the page that draw a file. */
	#drawing(path: string): HTMLElement[] {
		return this.#sections.all.filter((section) => section.path === path).map((section) => section.element);
	}

	/** Lines drawn in a section, by their keys, and the file they are of; null for a section not drawn. */
	#linesOf(sectionKey: string, lines: readonly string[]): LinesRead | null {
		const path = this.fileOf(sectionKey);
		return path === null ? null : { path, lines };
	}

	/** The section an element is drawn in, where it is in one: the nearest of its own and the elements round it. */
	#sectionHolding(element: Element): Section | null {
		for (let looked: Element | null = element; looked !== null; looked = looked.parentElement) {
			const section = this.#sections.of(looked);
			if (section !== undefined) return section;
		}
		return null;
	}

	/**
	 * Go to a line's number in a section, if this is still where the reader
	 * is taken: now where it is drawn, or once its section, brought into
	 * view, has its rows built and has come to rest.
	 */
	#reachLine(taking: number, sectionKey: string, arrived: LineArrivedAt): void {
		const section = this.#sections.get(sectionKey);
		if (taking !== this.#taken || section === undefined) return;
		const line = lineIn(section.element, arrived.line);
		if (line) this.#arriveAtLine(sectionKey, arrived, line);
		else this.#jumps.land(this.#sections.band, section.element, () => this.#arriveAtLineIn(section, arrived));
	}

	/** Go to a line's number in a section, if it is drawn there. */
	#arriveAtLineIn(section: Section, arrived: LineArrivedAt): void {
		const line = lineIn(section.element, arrived.line);
		if (line) this.#arriveAtLine(section.key, arrived, line);
	}

	/** Go to a line's number, and light the line arrived at. */
	#arriveAtLine(sectionKey: string, arrived: LineArrivedAt, line: HTMLElement): void {
		this.#arriveAt(line);
		this.arrived.light(sectionKey, arrived, line);
	}

	/**
	 * Take the reader to a thread on lines now if it is drawn, or once its
	 * rows are built, if that is soon; its section, gone to meanwhile, is
	 * still gone to once its view is drawn.
	 */
	#reachThread(threadId: string): void {
		const drawn = this.#threads.get(threadId);
		if (drawn) {
			this.#beginTaking();
			this.#arriveAt(drawn);
		} else {
			this.#awaitedThread = { threadId, until: performance.now() + AWAIT_ROWS_FOR };
		}
	}

	/**
	 * The reader is being taken somewhere now: whatever was asked for before,
	 * and is not drawn yet, is waited for no longer. Returns which taking
	 * this is.
	 */
	#beginTaking(): number {
		this.#awaitedThread = null;
		return ++this.#taken;
	}

	/**
	 * Take the reader to what `find` finds, as `arrive` does: now if it is
	 * drawn, or once Svelte has drawn what is pending — the view that draws
	 * it may have only just come on screen — unless the reader was taken
	 * somewhere else meanwhile. What its view does not draw by then is not
	 * waited for.
	 */
	#onceDrawn<Drawn>(find: () => Drawn | undefined, arrive: (drawn: Drawn) => void): void {
		const taking = this.#beginTaking();
		const drawn = find();
		if (drawn === undefined) void tick().then(() => this.#arriveOnceDrawn(taking, find, arrive));
		else arrive(drawn);
	}

	/** Arrive where `find` finds, now that what was pending is drawn, if this is still where the reader is taken. */
	#arriveOnceDrawn<Drawn>(taking: number, find: () => Drawn | undefined, arrive: (drawn: Drawn) => void): void {
		const drawn = find();
		if (taking === this.#taken && drawn !== undefined) arrive(drawn);
	}

	/**
	 * Bring a section that is drawn to the top at once: it is the one being
	 * read from now on, whatever the band says while it is on its way.
	 */
	#scrollToDrawn({ element }: Section): void {
		this.#jumps.land(this.#sections.band, element);
	}

	/** Bring a section that is drawn to the top at once, as the one being read from now on, and mark it once it has come to rest. */
	#showDrawn({ element }: Section): void {
		this.#unmark();
		this.#jumps.land(this.#sections.band, element, () => this.#mark(element));
	}

	/**
	 * Take the reader to a thread or a line's number at once, to the middle
	 * of its scrolling area, and put the keyboard on it: the reader is there
	 * now, and the next key — a line down, the next file, marking it viewed —
	 * acts from there rather than from where the keyboard was before. The
	 * jump puts it where it goes, so taking the keyboard does not move the
	 * screen again.
	 */
	#arriveAt(element: HTMLElement): void {
		this.#jumps.to(element, 'center');
		element.focus({ preventScroll: true });
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

	#unregisterBlock(blockKey: string, asking: HTMLElement): void {
		if (this.#blocks.get(blockKey) === asking) this.#blocks.delete(blockKey);
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

/** A line's number drawn in a section, by the key its place is known by; null where the section does not draw it. */
function lineIn(section: HTMLElement, lineKey: string): HTMLElement | null {
	return section.querySelector<HTMLElement>(`[data-place="${lineKey}"]`);
}

/** A line's number in the first of some sections to draw it; null where none does. */
function lineAmong(sections: HTMLElement[], lineKey: string): HTMLElement | null {
	return sections.map((section) => lineIn(section, lineKey)).find((found) => found !== null) ?? null;
}

/** Put the keyboard on the line gone back to, or where none is drawn on the section's own toggle, the screen left still. */
function keyboardToPlace(section: Section, line: HTMLElement | null): void {
	(line ?? toggleOf(section.element))?.focus({ preventScroll: true });
}

/** The toggle that folds a file's section: what stands for the file where nothing in it is drawn to stand for; null where the section folds nothing. */
function toggleOf(section: HTMLElement | null): HTMLElement | null {
	return section?.querySelector<HTMLElement>(`[data-role="${FOLD_TOGGLE_ROLE}"]`) ?? null;
}
