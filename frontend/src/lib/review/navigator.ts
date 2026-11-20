/**
 * Moving the reader through the review: from thread to thread, whatever
 * each hangs on, from section to section, and to a file or a line somebody
 * names.
 *
 * Naming a thread is the anchor's business and touches nothing; bringing one
 * into view opens what hides it and moves the screen, so it lives here, with
 * the parts of the page it moves — and so does where the reader has got to
 * among the threads, which only moving changes. Every control that takes the
 * reader to a thread moves them through here — n and p, a, the header's
 * arrows, the replies, the finish pane, the panel's chips, the notices — and
 * so do ] and [ from section to section, a file the agent names, a line
 * somebody names — where a check failed — and Back from it. What is
 * walked, and where a thread or a file is drawn, is asked of the view the
 * review is read in (`ReadingView`). No view draws everything by itself: a
 * story draws what it tells and leaves out, the files under a narrower base
 * what that base shows, the change's files no file the change did not
 * touch. What the view on screen does not draw is gone to in the view of
 * the Files way of reading that draws it — the change's files, read
 * against the review's own base, or a file read alone — which the views
 * bring on screen for it. The page itself is moved by `FileSections`. j and
 * k move the keyboard line by line there (`FileSections.stepLine`), and
 * have no place among the threads to keep.
 */

import { threadPlaceOf, type ThreadLines } from '$lib/anchors/views';
import type { FileSections } from '$lib/dom/file-sections';
import { fileSectionKey, type ReadingView, type ReadingViewName } from '$lib/review/reading-view';
import type { Threads } from '$lib/review/threads.svelte';
import type { PlaceLeft, WayBack } from '$lib/review/way-back.svelte';
import type { Thread } from '$lib/types';
import { placeKey } from '$lib/utils/line-places';

/** The views the review is read in, as moving the reader needs them. */
export interface ViewsOnScreen {
	/** The view the review is read in now. */
	readonly onScreen: ReadingView;
	/**
	 * Bring on screen the change's files, read against the review's own base,
	 * and hand their view over: as it is, where that base could not be
	 * brought back, and then it may draw less. It need not be drawn yet: the
	 * page waits for a section asked for before it is.
	 */
	showTheChange: () => Promise<ReadingView>;
	/** Bring a file the change did not touch on screen alone, at once, and hand its view over once it is read. */
	readAlone: (path: string) => Promise<ReadingView>;
	/** Bring on screen the view of the Files way of reading that draws a thread on these lines, and hand it over. */
	showWhereRead: (lines: ThreadLines) => Promise<ReadingView>;
	/** Bring a view on screen, as it draws the review now, and hand it over: how the reader chose to read stays. */
	show: (name: ReadingViewName) => ReadingView;
}

// The view that alone draws the threads on the story's words; the one a file the change did not touch is read
// alone in; and the one it is put away to, where the reader came to it from nowhere
const STORY: ReadingViewName = 'story';
const FILE_ALONE: ReadingViewName = 'file-alone';
const FILES: ReadingViewName = 'files';

/** Whether a place was left in a file read alone. */
function leftIn(path: string, left: PlaceLeft): boolean {
	return left.view === FILE_ALONE && left.place.within === fileSectionKey(path);
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
	// The places the reader left as they were taken to a line, which Back takes them to
	readonly #wayBack: WayBack;

	constructor(threads: Threads, sections: FileSections, views: ViewsOnScreen, wayBack: WayBack) {
		this.#threads = threads;
		this.#sections = sections;
		this.#views = views;
		this.#wayBack = wayBack;
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
	 * screen does not draw is gone to in the view of the Files way of
	 * reading that draws it, which comes on screen for it: the reader asked
	 * for the thread. Coming into a file read alone notes the place left for
	 * Back. Where the whole review cannot be put back for it, the files are
	 * on screen as their base has them, their bar says why, and the thread
	 * is not gone to.
	 * A thread on the story's words is drawn by the story alone, which comes
	 * on screen for it.
	 */
	reveal(thread: Thread): void {
		const place = threadPlaceOf(thread.anchor);
		switch (place.on) {
			case 'lines':
				this.#revealOnLines(thread, place.lines);
				break;
			case 'story':
				this.#revealOnTheStory(thread);
				break;
		}
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
	 * draws none of is shown among the change's files, which come on screen
	 * for it; one not drawn there either is shown nowhere.
	 */
	showFile(path: string): void {
		const section = this.#views.onScreen.sectionOfFile(path);
		if (section !== null) this.#sections.show(section);
		else void this.#views.showTheChange().then((files) => this.#showIn(files, path));
	}

	/**
	 * Take the reader into a file the change did not touch, to read it
	 * alone from its head, from where they pick it: the tree's row of it.
	 * Where they were is noted for Back.
	 */
	async readAlone(path: string): Promise<void> {
		const left = this.#placeRead();
		const alone = await this.#views.readAlone(path);
		this.#noteComingInto(left, alone, path);
		const section = alone.sectionOfFile(path);
		if (section !== null) this.#sections.scrollTo(section);
	}

	/**
	 * Take the reader out of a file read alone: back to where they were
	 * before they came into it, past every place they left within it, or,
	 * where they came from nowhere, to the change's files.
	 */
	async putAway(path: string): Promise<void> {
		while (this.#wayBack.top !== null && leftIn(path, this.#wayBack.top)) this.#wayBack.takeTop();
		if (this.#wayBack.top === null) this.#views.show(FILES);
		else await this.goBack();
	}

	/**
	 * Take the reader to a line of a file as it stands, with the keyboard on
	 * its number, in the middle of the reading area: where the view on
	 * screen draws it, its file unfolded and what the diff left out around
	 * it read in, or else among the change's files, which come on screen for
	 * it. A line drawn nowhere is not gone to. Where the reader was is read
	 * first, and noted for Back once they are taken somewhere else.
	 */
	async goToLine(path: string, line: number): Promise<void> {
		const left = this.#placeRead();
		const lineKey = placeKey({ side: 'new', number: line });
		const onScreen = await this.#views.onScreen.drawLine(path, line);
		if (onScreen !== null) {
			this.#goToLineFrom(left, onScreen, lineKey);
			return;
		}
		const files = await this.#views.showTheChange();
		const section = await files.drawLine(path, line);
		if (section !== null) this.#goToLineFrom(left, section, lineKey);
	}

	/**
	 * Take the reader back to the last place they left in the take on
	 * screen, as they saw it: in the view they read it in, how they chose
	 * to read left as it is, or among the change's files where that view
	 * cannot draw the place now. The place is taken off the way back, and
	 * going there notes none.
	 */
	async goBack(): Promise<void> {
		const left = this.#wayBack.takeTop();
		if (left === null) return;
		if (await this.#views.show(left.view).returnTo(left.place)) return;
		const files = await this.#views.showTheChange();
		await files.returnTo(left.place);
	}

	/** Where the reader reads, in the view on screen. */
	#placeRead(): PlaceLeft | null {
		const onScreen = this.#views.onScreen;
		const read = onScreen.placeRead();
		return read === null ? null : { ...read, view: onScreen.name };
	}

	/**
	 * Go to a line's number in a section, noting the place left for Back
	 * where the reader is taken somewhere else: a line they see already
	 * leaves them looking at what they saw, and Back would lead nowhere.
	 */
	#goToLineFrom(left: PlaceLeft | null, section: string, lineKey: string): void {
		if (left !== null && !this.#sections.seesLine(section, lineKey)) this.#wayBack.note(left);
		this.#sections.goToLine(section, lineKey);
	}

	/** Bring a thread on lines of a file into view, where the view on screen draws them or else where Files does. */
	#revealOnLines(thread: Thread, lines: ThreadLines): void {
		const onScreen = this.#views.onScreen;
		if (onScreen.sectionOf(lines) !== null) this.#revealIn(onScreen, thread, lines);
		else void this.#revealWhereRead(thread, lines);
	}

	/** Bring a thread on lines into view in the view of the Files way of reading that draws it, brought on screen for it. */
	async #revealWhereRead(thread: Thread, lines: ThreadLines): Promise<void> {
		const left = this.#placeRead();
		const drawing = await this.#views.showWhereRead(lines);
		this.#noteComingInto(left, drawing, lines.file);
		this.#revealIn(drawing, thread, lines);
	}

	/** Note the place left for Back where the reader comes into a file read alone from anywhere else. */
	#noteComingInto(left: PlaceLeft | null, view: ReadingView, path: string): void {
		if (left !== null && view.name === FILE_ALONE && !leftIn(path, left)) this.#wayBack.note(left);
	}

	/** Bring a thread on the story's words into view in the story, which comes on screen for it. */
	#revealOnTheStory(thread: Thread): void {
		const story = this.#views.show(STORY);
		this.#at = { thread: thread.id, among: story.threadsInOrder() };
		this.#sections.goToStoryThread(thread.id);
	}

	/** Go to a thread on lines in a view, if the view draws them. */
	#revealIn(view: ReadingView, thread: Thread, lines: ThreadLines): void {
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
