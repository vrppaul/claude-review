/**
 * How this reader lays the page out: the file tree, the contents beside a
 * story, the agent panel, how a renderable file is shown, and which way a
 * review is read.
 *
 * None of these belong to a review — they are how this person reads this
 * page — so they are kept in this port's storage, not with the review and
 * not on the server.
 *
 * A column the reader has not opened or shut themselves comes on screen of
 * its own only where it stands beside the diff: below its breakpoint it
 * would lie over the code, and a review opened under its columns, or
 * covered the moment an agent turns up, is no way to start reading. The
 * reader's own choice stands on any screen.
 */

import { SvelteSet } from 'svelte/reactivity';
import { screenReaches } from '$lib/dom/screen';
import { readChoice, readFlag, readNumber, writeChoice } from '$lib/utils/preferences';

/** How narrow and how wide a column may be, and how wide it starts. */
interface WidthBounds {
	min: number;
	max: number;
	fallback: number;
}

// Narrower than this and a path is unreadable; wider and the column takes the
// room from the code it is a table of contents for: the tree of files, and a
// story's contents, which name files too
const SIDE_COLUMN_WIDTH: WidthBounds = { min: 160, max: 560, fallback: 240 };
// Below this there is no room for a sentence; above it the diff — which the
// conversation is about — stops being readable
const AGENT_PANEL_WIDTH: WidthBounds = { min: 280, max: 720, fallback: 380 };

// The names each choice is kept under in this port's storage
const FILE_TREE_OPEN_KEY = 'sidebar-open';
const SIDE_COLUMN_WIDTH_KEY = 'sidebar-width';
const STORY_CONTENTS_OPEN_KEY = 'contents-open';
const AGENT_PANEL_OPEN_KEY = 'panel-open';
const AGENT_PANEL_WIDTH_KEY = 'panel-width';
const CONTENT_VIEW_KEY = 'content-view';
const READING_VIEW_KEY = 'reading-view';

// Where a column stops lying over the diff and stands beside it, as the stylesheet names it: one
// the reader puts away, which the stylesheet draws as its side column, and the panel
const PUT_AWAY_BESIDE = '--breakpoint-cr-side-column-beside';
const AGENT_PANEL_BESIDE = '--breakpoint-cr-panel-beside';

/** Every way a renderable file can be shown: as text, rendered, or both side by side. */
const CONTENT_VIEW_MODES = ['raw', 'preview', 'side-by-side'] as const;
export type ContentViewMode = (typeof CONTENT_VIEW_MODES)[number];
const FIRST_CONTENT_VIEW: ContentViewMode = 'raw';

/** Every way a review can be read: file by file, or as the story the agent tells of it. */
const READING_VIEWS = ['files', 'story'] as const;
export type ReadingViewName = (typeof READING_VIEWS)[number];
const FIRST_READING_VIEW: ReadingViewName = 'files';

// Whether the reader has said if they want the agent panel: "unset" until
// they open or shut it themselves
const PANEL_CHOICES = ['on', 'off'] as const;
type PanelChoice = (typeof PANEL_CHOICES)[number] | 'unset';

/**
 * A column's width, held to its bounds and kept in this port's storage.
 *
 * A width saved on a wide screen must not leave a narrow one with no room
 * for the diff, so the bounds hold on the way in as well as on the way out.
 */
class StoredWidth {
	readonly #key: string;
	readonly #bounds: WidthBounds;
	#value: number;

	constructor(key: string, bounds: WidthBounds) {
		this.#key = key;
		this.#bounds = bounds;
		this.#value = $state(readNumber(key, bounds));
	}

	get value(): number {
		return this.#value;
	}

	/** How narrow and how wide it may be. */
	get bounds(): WidthBounds {
		return this.#bounds;
	}

	set(next: number): void {
		const { min, max } = this.#bounds;
		this.#value = Math.min(max, Math.max(min, Math.round(next)));
		writeChoice(this.#key, this.#value);
	}
}

/**
 * A column beside what is read, which the reader puts away to its rail and
 * brings back, on either side: on screen or not, and how wide.
 */
class PutAwayColumn {
	readonly #openKey: string;
	#open: boolean;
	readonly #width: StoredWidth;

	/**
	 * @param openKey the name whether it is on screen is kept under
	 * @param width how wide it is: a width it may share, as the tree and a story's contents do, whichever view it stands in
	 * @param openUnchosen whether it is on screen before the reader has opened or shut it themselves
	 */
	constructor(openKey: string, width: StoredWidth, openUnchosen: boolean) {
		this.#openKey = openKey;
		this.#open = $state(readFlag(openKey, openUnchosen));
		this.#width = width;
	}

	/** Whether the column is on screen. Put away, it gives its room back to what is read, but for its rail. */
	get open(): boolean {
		return this.#open;
	}

	get width(): number {
		return this.#width.value;
	}

	get least(): number {
		return this.#width.bounds.min;
	}

	get most(): number {
		return this.#width.bounds.max;
	}

	/** The reader puts it away or brings it back, which is kept as their choice. */
	setOpen(next: boolean): void {
		this.#open = next;
		writeChoice(this.#openKey, next);
	}

	toggle(): void {
		this.setOpen(!this.#open);
	}

	setWidth(next: number): void {
		this.#width.set(next);
	}

	/** Bring it on screen of its own accord, the reader having chosen nothing: nothing is kept. */
	protected comeOnScreen(): void {
		this.#open = true;
	}
}

/**
 * The file tree: a column the reader puts away, and how they left it — what
 * they were looking for in it, and the folders they folded. Those two
 * outlive the tree being put away and brought back, not a reload.
 */
class FileTreeLayout extends PutAwayColumn {
	#filter = $state('');
	readonly #foldedFolders = new SvelteSet<string>();

	/** @param width how wide it is, as wide as a story's contents */
	constructor(width: StoredWidth) {
		super(FILE_TREE_OPEN_KEY, width, screenReaches(PUT_AWAY_BESIDE));
	}

	/** What the reader typed into the tree's filter. */
	get filter(): string {
		return this.#filter;
	}

	setFilter(next: string): void {
		this.#filter = next;
	}

	isFolderFolded(path: string): boolean {
		return this.#foldedFolders.has(path);
	}

	toggleFolder(path: string): void {
		if (this.#foldedFolders.has(path)) this.#foldedFolders.delete(path);
		else this.#foldedFolders.add(path);
	}
}

/**
 * The agent panel: a column put away and brought back as the tree is, and
 * how many answers landed while it was put away, so its rail can say so.
 */
class AgentPanelLayout extends PutAwayColumn {
	// Until the reader has said whether they want the panel, it opens itself
	// when an agent turns up and stays out of the way otherwise: an empty
	// panel beside a review nobody is answering is a column of nothing
	#chosen = readChoice<PanelChoice>(AGENT_PANEL_OPEN_KEY, PANEL_CHOICES, 'unset') !== 'unset';
	#unread = $state(0);
	// The cursor was asked into the panel's field, which has not taken it yet:
	// the field may not be drawn until the panel opens
	#inputWanted = $state(false);

	constructor() {
		super(AGENT_PANEL_OPEN_KEY, new StoredWidth(AGENT_PANEL_WIDTH_KEY, AGENT_PANEL_WIDTH), false);
	}

	/** Answers that landed while the panel was put away. */
	get unread(): number {
		return this.#unread;
	}

	/** The reader's choice, from which on it no longer opens itself; brought back, what landed meanwhile is read. */
	override setOpen(next: boolean): void {
		super.setOpen(next);
		this.#chosen = true;
		if (next) this.#unread = 0;
	}

	/** An agent has turned up; show the panel unless the reader shut it, or it would lie over the diff. */
	offer(): void {
		if (!this.#chosen && screenReaches(AGENT_PANEL_BESIDE)) this.comeOnScreen();
	}

	/** Whether the cursor is waiting to be put in the panel's field. */
	get inputWanted(): boolean {
		return this.#inputWanted;
	}

	/** Put the cursor in the panel's field, as soon as there is one. */
	askForInput(): void {
		this.#inputWanted = true;
	}

	/** The field has the cursor. */
	inputTaken(): void {
		this.#inputWanted = false;
	}

	/** An answer landed in the conversation; count it if nobody can see it. */
	noteAnswer(): void {
		if (!this.open) this.#unread += 1;
	}
}

/** How a file that can be rendered is shown. */
class ContentViewChoice {
	#mode = $state(readChoice(CONTENT_VIEW_KEY, CONTENT_VIEW_MODES, FIRST_CONTENT_VIEW));

	get mode(): ContentViewMode {
		return this.#mode;
	}

	set(mode: ContentViewMode): void {
		this.#mode = mode;
		writeChoice(CONTENT_VIEW_KEY, mode);
	}
}

/** Which way the reader reads a review: the one they chose last, whether or not a review can be read that way. */
class ReadingViewChoice {
	#name = $state(readChoice(READING_VIEW_KEY, READING_VIEWS, FIRST_READING_VIEW));

	get name(): ReadingViewName {
		return this.#name;
	}

	set(name: ReadingViewName): void {
		this.#name = name;
		writeChoice(READING_VIEW_KEY, name);
	}
}

/** Everything about how the page is laid out, as this reader left it. */
export class PageLayout {
	// How wide the column beside what is read stands: the tree of files, or a story's contents
	readonly #sideColumnWidth = new StoredWidth(SIDE_COLUMN_WIDTH_KEY, SIDE_COLUMN_WIDTH);
	readonly fileTree = new FileTreeLayout(this.#sideColumnWidth);
	/** The contents beside a story: put away by itself, whatever the tree of files is, and as wide as it. */
	readonly storyContents = new PutAwayColumn(
		STORY_CONTENTS_OPEN_KEY,
		this.#sideColumnWidth,
		screenReaches(PUT_AWAY_BESIDE)
	);
	readonly agentPanel = new AgentPanelLayout();
	readonly contentView = new ContentViewChoice();
	readonly readingView = new ReadingViewChoice();
}
