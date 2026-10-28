/**
 * A reader's feedback on claude-review itself: what they write in the card
 * Help opens, the issue the review writes of it, and where it went.
 *
 * The words are kept while the page lives, so closing the card loses
 * nothing; once they went, they are no longer a draft. Every word of the
 * issue is the server's (`services/feedback.py`), asked for again whenever a
 * row is ticked or unticked, so what the preview shows is always what goes.
 * Nothing leaves the review from here: the reader opens the issue on GitHub
 * themselves, or hands it to their agent as a message of the panel.
 */

import { writeFeedbackIssue } from '$lib/api/review-api';
import type { PointedPart } from '$lib/dom/part-picking';
import type { FeedbackIssue, FeedbackKind, FeedbackReading, GoesWithIt } from '$lib/types';
import { messageOf } from '$lib/utils/errors';

/**
 * Where the feedback went: opened on GitHub filled in, opened there with its title alone and its text copied as
 * too long to fill in, or handed to the agent.
 */
export type FeedbackWent = 'opened' | 'too-long' | 'handed';

/**
 * Where the card stands: being written; the issue shown to the letter before it goes; or where it went. Each
 * step past the writing holds the issue it shows or sent.
 */
export type FeedbackStage =
	| { step: 'writing' }
	| { step: 'preview'; issue: FeedbackIssue }
	| { step: 'went'; went: FeedbackWent; issue: FeedbackIssue };

// What a reader's feedback is until they say otherwise
const FIRST_KIND: FeedbackKind = 'bug';
// Every row goes until the reader unticks it: the preview shows each before anything leaves
const EVERY_ROW: ReadonlySet<GoesWithIt> = new Set(['machine', 'reading', 'part']);
const WRITING: FeedbackStage = { step: 'writing' };

/** The rows that go, with one of them ticked or unticked. */
function withRow(going: ReadonlySet<GoesWithIt>, row: GoesWithIt, goes: boolean): ReadonlySet<GoesWithIt> {
	const others = [...going].filter((each) => each !== row);
	return new Set(goes ? [...others, row] : others);
}

/** What the feedback needs of the page around it. */
export interface FeedbackSurroundings {
	/** What the reader is reading in now. */
	reading: () => FeedbackReading;
	/** Hand words to the agent as the reader's message in its panel; throws where they did not go. */
	handToAgent: (words: string) => Promise<void>;
}

export class Feedback {
	readonly #surroundings: FeedbackSurroundings;
	#kind = $state<FeedbackKind>(FIRST_KIND);
	#words = $state('');
	#going = $state.raw<ReadonlySet<GoesWithIt>>(EVERY_ROW);
	#stage = $state.raw<FeedbackStage>(WRITING);
	// Whether the reader is pointing at the page for the part they mean
	#pointing = $state(false);
	// The part under the pointer or the keyboard while they point
	#over = $state.raw<PointedPart | null>(null);
	// The part they pointed at, which goes as a row of its own; none until they point
	#part = $state.raw<PointedPart | null>(null);
	// How many times the issue was asked for: only the answer to the last is shown
	#asked = 0;
	// The issue on its way to the agent, so a second press does not hand it twice
	#handing = false;
	// Why the last thing tried did not happen, until the next is tried
	#failed = $state<string | null>(null);

	constructor(surroundings: FeedbackSurroundings) {
		this.#surroundings = surroundings;
	}

	get kind(): FeedbackKind {
		return this.#kind;
	}

	setKind(kind: FeedbackKind): void {
		this.#kind = kind;
	}

	get words(): string {
		return this.#words;
	}

	setWords(words: string): void {
		this.#words = words;
	}

	/** Whether anything is written: a draft kept while the card is closed, and the issue's words. */
	get written(): boolean {
		return this.#words.trim() !== '';
	}

	get stage(): FeedbackStage {
		return this.#stage;
	}

	isGoing(row: GoesWithIt): boolean {
		return this.#going.has(row);
	}

	get pointing(): boolean {
		return this.#pointing;
	}

	/** Point at the page for the part meant, or stop. */
	setPointing(pointing: boolean): void {
		this.#pointing = pointing;
		this.#over = null;
	}

	/** The part under the pointer or the keyboard, while the reader points. */
	get over(): PointedPart | null {
		return this.#over;
	}

	pointAt(part: PointedPart): void {
		this.#over = part;
	}

	get part(): PointedPart | null {
		return this.#part;
	}

	/** The part the reader pointed at: pointing ends with it. */
	take(part: PointedPart): void {
		this.#part = part;
		this.setPointing(false);
	}

	leavePartOut(): void {
		this.#part = null;
	}

	get failed(): string | null {
		return this.#failed;
	}

	/**
	 * Ask the review to write the issue of what is written and ticked now, and show it to the letter: only the
	 * last asked for, as a row may be ticked again before the answer to the one before comes.
	 */
	async preview(): Promise<void> {
		this.#asked += 1;
		const asked = this.#asked;
		this.#failed = null;
		try {
			const issue = await writeFeedbackIssue({
				kind: this.#kind,
				words: this.#words,
				reading: this.#surroundings.reading(),
				part: this.#part,
				going: [...this.#going]
			});
			if (asked === this.#asked) this.#stage = { step: 'preview', issue };
		} catch (error) {
			if (asked === this.#asked) this.#failed = messageOf(error);
		}
	}

	/** Tick a row or untick it: the issue is written again, so the text shown is always what goes. */
	async setGoing(row: GoesWithIt, going: boolean): Promise<void> {
		this.#going = withRow(this.#going, row, going);
		await this.preview();
	}

	/** Back to the words, to change them. */
	edit(): void {
		this.#stage = WRITING;
		this.#failed = null;
	}

	/**
	 * The reader followed the way to GitHub, which opens the issue in a tab of
	 * its own. One too long to open filled in opens with its title alone, and
	 * its text is copied to paste there.
	 */
	async openedOnGitHub(issue: FeedbackIssue): Promise<void> {
		this.#went(issue.filled ? 'opened' : 'too-long', issue);
		if (!issue.filled) await this.copyText(issue);
	}

	/** Hand the issue to the agent, which looks for one like it and shows the reader what it will file. */
	async handToAgent(issue: FeedbackIssue): Promise<void> {
		if (this.#handing) return;
		this.#handing = true;
		this.#failed = null;
		try {
			await this.#surroundings.handToAgent(issue.for_agent);
			this.#went('handed', issue);
		} catch (error) {
			this.#failed = messageOf(error);
		} finally {
			this.#handing = false;
		}
	}

	/** Copy the issue's text, to paste where it opened. */
	async copyText(issue: FeedbackIssue): Promise<void> {
		this.#failed = null;
		try {
			await navigator.clipboard.writeText(issue.body);
		} catch (error) {
			this.#failed = messageOf(error);
		}
	}

	/** The card is put away: what is written stays for the next time it opens, and where it went is forgotten. */
	putAway(): void {
		this.#stage = WRITING;
		this.setPointing(false);
		this.#failed = null;
	}

	/** The feedback went: what was written is no draft any more, and the next begins as the first did. */
	#went(went: FeedbackWent, issue: FeedbackIssue): void {
		this.#stage = { step: 'went', went, issue };
		this.#kind = FIRST_KIND;
		this.#words = '';
		this.#part = null;
		this.#going = EVERY_ROW;
	}
}
