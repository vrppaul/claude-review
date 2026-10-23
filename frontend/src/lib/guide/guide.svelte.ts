/**
 * Showing a reader around: the welcome, what is new, the tour, and Story.
 *
 * One card, bottom left. Somebody who has never opened a review is
 * welcomed; somebody whose last review was an older release is told what
 * changed, when there is anything to tell; everybody else sees nothing.
 * The tour narrates from that same card while a light moves over the review.
 *
 * Story, a way of reading the reader may never have tried, is introduced
 * once: by the news of the release that brought it, by the tour's stop at
 * it, or else at the switch, once the card and the tour are done. It counts
 * as introduced once that news was shown, once the tour stopped there, once
 * the reader said at the switch not to show it again, or once they tried
 * it, by pressing it or with the story on screen; that is kept for every
 * review on the machine, as the release seen is.
 */

import { keepGuide, readGuide } from '$lib/api/review-api';
import type { CommentRoute, TourStep, TourTarget } from '$lib/guide/tour';
import type { CommentFieldEvent, GuideState } from '$lib/types';
import { DRAWN_BY_THE_READER, TOUR_STEPS, stepsFor } from '$lib/guide/tour';
import { RELEASE_NEWS, type ReleaseNews } from '$lib/guide/news';
import { isNewer, latestNews, unseenNews } from '$lib/guide/news-choice';
import { handOverLegacyRelease, legacySeenRelease, writeSeenRelease } from '$lib/guide/seen-release';

export type GuideCard = 'welcome' | 'news';

/** Whether Story has been introduced to the reader, as far as this page knows: before the server says, it does not. */
type StoryIntroduced = 'unknown' | 'introduced' | 'not';

/** Whoever answers the review, as far as the tour cares: whether anyone is there to send a round to. */
export interface AnswererPresence {
	readonly attached: boolean;
}

/**
 * The comments being written, as far as the tour cares: how many are open
 * on lines — counted where they are held, so those a reload brought back
 * count as well.
 */
export interface OpenComments {
	readonly openOnLines: number;
}

/**
 * What the reader did that a step was waiting for: opened a comment on a
 * line, or sent one, to the review or straight to the agent.
 */
type Done = { kind: 'opened' } | { kind: 'sent'; route: CommentRoute };

/** Whether two sets hold the same members. */
function sameMembers<Member>(first: ReadonlySet<Member>, second: ReadonlySet<Member>): boolean {
	return first.size === second.size && [...first].every((member) => second.has(member));
}

/** Where a step stands among the steps that are shown, by its id. */
function indexOfStep(shown: TourStep[], id: string | null): number {
	const at = shown.findIndex((step) => step.id === id);
	if (at !== -1 || id === null) return Math.max(at, 0);
	// A step this tour no longer has — an agent joined, or left — is stood in
	// for by the nearest step before it in the whole tour that it still has:
	// saving a comment becomes choosing where it goes, the last word becomes
	// the round or the end
	const inWholeTour = TOUR_STEPS.findIndex((step) => step.id === id);
	const standIn = TOUR_STEPS.slice(0, Math.max(inWholeTour, 0)).findLast((step) => shown.includes(step));
	return standIn ? shown.indexOf(standIn) : 0;
}

export class Guide {
	readonly #answerer: AnswererPresence;
	// Comment fields on a line open right now, so a step asking for one that
	// is already open does not wait for something that has happened
	readonly #comments: OpenComments;
	// Which release serves this review
	readonly #release: string;
	// Say that whether Story is introduced again could not be kept, as the page says what a request came to
	readonly #notKept: (error: unknown) => void;
	#card = $state<GuideCard | null>(null);
	// The ? list: the tour, the news and the keys. Opened by the key or by the
	// button in the header — a browser extension may have the key for itself.
	#helpOpen = $state(false);
	#news = $state.raw<ReleaseNews | undefined>(undefined);
	#touring = $state(false);
	// Whether Story has been introduced to the reader: unknown until the server
	// says, and where it cannot
	#storyIntroduced = $state<StoryIntroduced>('unknown');
	// The introduction put away by its cross: for this page alone, kept nowhere
	#introductionPutAway = $state(false);
	// The step on screen, by name: the tour's steps change when an agent joins
	// or leaves, and a position would then point at a different step
	#stepId = $state<string | null>(null);
	#route = $state<CommentRoute>('review');
	// Which places the page has drawn for a step to light. The page says so
	// while it is watched; until it first has, every step counts as shown,
	// and a step landed on then is checked again once it has.
	#onPage = $state.raw<ReadonlySet<TourTarget> | null>(null);
	// What the reader did that the step on screen waited for, held until the
	// page next says what it has drawn: the step it leads to lights what the
	// reader just drew, which is on the page only once the page says so
	#done: Done | null = null;
	readonly #steps: TourStep[];
	readonly #stepIndex: number;
	// The tour's stops, one list for every count of them: the welcome's, the
	// ? list's and the tour's own
	readonly #stops: TourStep[];

	constructor(answerer: AnswererPresence, comments: OpenComments, release: string, notKept: (error: unknown) => void) {
		this.#answerer = answerer;
		this.#comments = comments;
		this.#release = release;
		this.#notKept = notKept;
		this.#steps = $derived(stepsFor({ attached: this.#answerer.attached, route: this.#route }));
		this.#stepIndex = $derived(indexOfStep(this.#steps, this.#stepId));
		this.#stops = $derived(this.#steps.filter((step) => this.#isStop(step)));
	}

	get card(): GuideCard | null {
		return this.#card;
	}

	get helpOpen(): boolean {
		return this.#helpOpen;
	}

	setHelpOpen(open: boolean): void {
		this.#helpOpen = open;
	}

	get news(): ReleaseNews | undefined {
		return this.#news;
	}

	get touring(): boolean {
		return this.#touring;
	}

	/**
	 * Whether Story is introduced at the switch now: to a reader it was never
	 * introduced to, who has not put it away on this page. It waits while the
	 * card or the tour stands, so the two never stand together; and while the
	 * server has not said, as when it cannot, it is not introduced: better not
	 * introduced than introduced twice.
	 */
	get introducesStory(): boolean {
		return this.#storyIntroduced === 'not' && !this.#introductionPutAway && this.#card === null && !this.#touring;
	}

	/**
	 * Story has been introduced to the reader, or tried by them: kept, for every review, and never introduced again.
	 * Kept also before the server has said whether it was before, which then changes nothing.
	 */
	noteStoryIntroduced(): void {
		if (this.#storyIntroduced === 'introduced') return;
		this.#storyIntroduced = 'introduced';
		this.#keepStoryIntroduced(true);
	}

	/** The reader undid "Don't show again": Story is introduced again, here and in every review. */
	introduceStoryAgain(): void {
		this.#storyIntroduced = 'not';
		this.#keepStoryIntroduced(false);
	}

	/** Put the introduction away for this page alone: it comes back in the next review. */
	putIntroductionAway(): void {
		this.#introductionPutAway = true;
	}

	/**
	 * Whether what the page has drawn matters now: the tour runs, or the
	 * welcome or the ? list says how many stops it has.
	 */
	get watchesThePage(): boolean {
		return this.#touring || this.#card === 'welcome' || this.#helpOpen;
	}

	get step(): TourStep | undefined {
		return this.#touring ? this.#steps[this.#stepIndex] : undefined;
	}

	/**
	 * Where this step stands among the tour's stops — a plan has no base to
	 * choose, so its tour is shorter, and says so.
	 */
	get stepPosition(): number {
		const current = this.#steps[this.#stepIndex];
		return current ? this.#stops.indexOf(current) : -1;
	}

	/** How many stops the tour has, as the welcome, the ? list and the tour itself all say. */
	get stepCount(): number {
		return this.#stops.length;
	}

	get isLastStep(): boolean {
		return !this.#steps.slice(this.#stepIndex + 1).some((step) => this.#shows(step));
	}

	/** Whether there is a step before this one to go back to. */
	get canGoBack(): boolean {
		return this.#steps.slice(0, this.#stepIndex).some((step) => this.#shows(step));
	}

	/** The newest news up to this release, to read again from the ? list. */
	get latestNews(): ReleaseNews | undefined {
		return latestNews(RELEASE_NEWS, this.#release);
	}

	/**
	 * The page says which of the tour's places it has drawn, each time it has
	 * drawn anything. What the reader did that the step waited for moves the
	 * tour on now, once what it drew is on the page. A step left with nothing
	 * to light — the tour began before the page could say — moves on to the
	 * next that has something.
	 */
	seeTargets(drawn: ReadonlySet<TourTarget>): void {
		const before = this.#onPage;
		const landedBlind = before === null;
		if (before === null || !sameMembers(drawn, before)) this.#onPage = drawn;
		const done = this.#done;
		this.#done = null;
		if (done) {
			this.#moveOn(done);
			return;
		}
		const current = this.step;
		if (landedBlind && current && !this.#shows(current)) this.#landFrom(this.#stepIndex, 1);
	}

	/** The page is no longer watched, so what it last said goes stale. */
	pageUnwatched(): void {
		this.#onPage = null;
	}

	/**
	 * Decide what to show a reader arriving at a review served by this
	 * release, from what the server keeps of having shown them around.
	 * Nothing, when the server cannot say: a reader who cannot be told apart
	 * from a newcomer is better left unwelcomed than welcomed twice.
	 */
	async open(): Promise<void> {
		let kept: GuideState;
		let seen: string | null;
		try {
			kept = (await readGuide()).record;
			seen = kept.seen_release ?? (await this.#fromLegacyCookie());
		} catch {
			return;
		}
		// A reader who tried Story while the server was asked has been introduced to it, whatever it kept
		if (this.#storyIntroduced === 'unknown') this.#storyIntroduced = kept.story_introduced ? 'introduced' : 'not';
		if (seen === null) {
			this.#card = 'welcome';
			return;
		}
		if (!isNewer(this.#release, seen)) return;
		const unseen = unseenNews(RELEASE_NEWS, seen, this.#release);
		if (unseen) this.#show(unseen);
		// Nothing worth telling: a patch is remembered as seen without a word
		else this.#settle();
	}

	/** Put the card away, for this release. */
	dismiss(): void {
		this.#card = null;
		this.#settle();
	}

	showNews(): void {
		const latest = this.latestNews;
		if (latest) this.#show(latest);
	}

	startTour(): void {
		this.#card = null;
		this.#settle();
		this.#route = 'review';
		this.#touring = true;
		this.#landFrom(0, 1);
	}

	/** The tour is over, skipped or walked to its end. */
	endTour(): void {
		this.#touring = false;
		this.#done = null;
		// What the page said was said for this tour; the next asks afresh
		this.#onPage = null;
	}

	next(): void {
		this.#landFrom(this.#stepIndex + 1, 1);
	}

	back(): void {
		this.#landFrom(this.#stepIndex - 1, -1);
	}

	/**
	 * Hear what happened to a comment field. What a step was waiting for
	 * moves the tour on once the page next says what it has drawn — the step
	 * it leads to lights what was just drawn; a comment put away unsent goes
	 * back at once.
	 */
	notice(event: CommentFieldEvent): void {
		const waiting = this.step?.waitsFor;
		if (!waiting || event.kind !== 'new') return;

		if (waiting.kind === 'comment-opened') {
			if (event.type === 'opened') this.#done = { kind: 'opened' };
			return;
		}
		this.#followComment(event.type, waiting.routes);
	}

	/** The release a cookie from an older release says was seen, handed over to the server; null when there is none. */
	async #fromLegacyCookie(): Promise<string | null> {
		const legacy = legacySeenRelease();
		if (legacy !== null) await handOverLegacyRelease(legacy);
		return legacy;
	}

	/** Note where a comment the step was waiting to see sent went, or go back if it was dropped. */
	#followComment(happened: CommentFieldEvent['type'], routes: readonly CommentRoute[]): void {
		if (happened === 'added' && routes.includes('review')) {
			this.#done = { kind: 'sent', route: 'review' };
		} else if (happened === 'asked' && routes.includes('ask')) {
			this.#done = { kind: 'sent', route: 'ask' };
		} else if (happened === 'closed' && this.#comments.openOnLines === 0) {
			// While another comment on a line is open, that one is still to be sent
			this.#done = null;
			this.back();
		}
	}

	/** Move on from what the reader did; a comment sent shows next what came of it, the way it went. */
	#moveOn(done: Done): void {
		if (done.kind === 'sent') this.#route = done.route;
		this.next();
	}

	/** Show a release's news on the card; the news that introduces Story introduces it, so nothing at the switch follows. */
	#show(news: ReleaseNews): void {
		this.#news = news;
		this.#card = 'news';
		if (news.introducesStory) this.noteStoryIntroduced();
	}

	/** Remember this release as seen, so the card does not come back. */
	#settle(): void {
		// Not remembered this time, if it fails: the card comes back with the next review
		writeSeenRelease(this.#release).catch(() => undefined);
	}

	/**
	 * Keep whether Story has been introduced, for every review. Not kept, it
	 * is said: the reader chose, and the next review would introduce Story
	 * again without a word why.
	 */
	#keepStoryIntroduced(introduced: boolean): void {
		keepGuide({ story_introduced: introduced }).catch(this.#notKept);
	}

	/**
	 * Whether the tour lands on a step: one with something on the page to
	 * light, unless it waits for a comment on a line and one is open already.
	 */
	#shows(step: TourStep): boolean {
		const onPage = this.#onPage;
		if (onPage !== null && !step.targets.some((target) => onPage.has(target))) return false;
		return !(step.waitsFor?.kind === 'comment-opened' && this.#comments.openOnLines > 0);
	}

	/**
	 * Whether a step is one of the tour's stops: one with something on the
	 * page to light, or with what the reader is about to draw. A stop passed
	 * over because what it waits for is done already is still counted.
	 */
	#isStop(step: TourStep): boolean {
		const onPage = this.#onPage;
		return onPage === null || step.targets.some((target) => onPage.has(target) || DRAWN_BY_THE_READER.has(target));
	}

	/**
	 * Land on the first step from here, going this way, that has something to
	 * show.
	 *
	 * Going back past the start turns round, so the first step shown is always
	 * one there is something to see in; going on past the end ends the tour.
	 */
	#landFrom(index: number, direction: 1 | -1): void {
		const landing =
			direction === 1
				? this.#steps.slice(index).find((step) => this.#shows(step))
				: this.#steps.slice(0, index + 1).findLast((step) => this.#shows(step));
		if (landing) this.#landOn(landing);
		else if (direction === -1) this.#landFrom(0, 1);
		else this.endTour();
	}

	/** Show a step of the tour; the one that introduces Story introduces it, so nothing at the switch follows. */
	#landOn(step: TourStep): void {
		this.#stepId = step.id;
		if (step.introducesStory) this.noteStoryIntroduced();
	}
}
