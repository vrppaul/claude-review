/**
 * Showing a reader around: the welcome, what is new, and the tour.
 *
 * One card, bottom left. Somebody who has never opened a review is
 * welcomed; somebody whose last review was an older release is told what
 * changed, when there is anything to tell; everybody else sees nothing.
 * The tour narrates from that same card while a light moves over the review.
 */

import type { CommentRoute, TourStep, TourTarget } from '$lib/guide/tour';
import type { CommentFieldEvent } from '$lib/types';
import { TOUR_STEPS, stepsFor } from '$lib/guide/tour';
import { RELEASE_NEWS, type ReleaseNews } from '$lib/guide/news';
import { isNewer, latestNews, unseenNews } from '$lib/guide/news-choice';
import { handOverLegacyRelease, legacySeenRelease, readSeenRelease, writeSeenRelease } from '$lib/guide/seen-release';

export type GuideCard = 'welcome' | 'news';

/** Whoever answers the review, as far as the tour cares: whether anyone is there to send a round to. */
export interface AnswererPresence {
	readonly attached: boolean;
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
	for (let earlier = inWholeTour - 1; earlier >= 0; earlier -= 1) {
		const standIn = shown.findIndex((step) => step.id === TOUR_STEPS[earlier].id);
		if (standIn !== -1) return standIn;
	}
	return 0;
}

export class Guide {
	readonly #answerer: AnswererPresence;
	// Which release serves this review
	readonly #release: string;
	#card = $state<GuideCard | null>(null);
	// The ? list: the tour, the news and the keys. Opened by the key or by the
	// button in the header — a browser extension may have the key for itself.
	#helpOpen = $state(false);
	#news = $state<ReleaseNews | undefined>(undefined);
	#touring = $state(false);
	// The step on screen, by name: the tour's steps change when an agent joins
	// or leaves, and a position would then point at a different step
	#stepId = $state<string | null>(null);
	#route = $state<CommentRoute>('review');
	// Thread fields on a line open right now, so a step asking for one that
	// is already open does not wait for something that has happened
	#openNewComments = $state(0);
	// Which places the page has drawn for a step to light. The page says so
	// while the tour runs; until it first has, every step counts as shown,
	// and a step landed on then is checked again once it has.
	#onPage = $state<ReadonlySet<TourTarget> | null>(null);
	readonly #steps: TourStep[];
	readonly #stepIndex: number;

	constructor(answerer: AnswererPresence, release: string) {
		this.#answerer = answerer;
		this.#release = release;
		this.#steps = $derived(stepsFor({ attached: this.#answerer.attached, route: this.#route }));
		this.#stepIndex = $derived(indexOfStep(this.#steps, this.#stepId));
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

	get step(): TourStep | undefined {
		return this.#touring ? this.#steps[this.#stepIndex] : undefined;
	}

	/**
	 * Where this step stands among the steps the reader will actually see —
	 * a plan has no base to choose, so its tour is shorter, and says so.
	 */
	get stepPosition(): number {
		const current = this.#steps[this.#stepIndex];
		return current ? this.#shownSteps().indexOf(current) : -1;
	}

	get stepCount(): number {
		return this.#shownSteps().length;
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
	 * The page says which of the tour's places it has drawn. A step left with
	 * nothing to light — the tour began before the page could say — moves on
	 * to the next that has something.
	 */
	seeTargets(drawn: ReadonlySet<TourTarget>): void {
		const landedBlind = this.#onPage === null;
		this.#onPage = drawn;
		const current = this.step;
		if (landedBlind && current && !this.#shows(current)) this.#landFrom(this.#stepIndex, 1);
	}

	/** Decide what to show a reader arriving at a review served by this release. */
	async open(): Promise<void> {
		let seen: string | null;
		try {
			seen = (await readSeenRelease()) ?? (await this.#fromLegacyCookie());
		} catch {
			return;
		}
		if (seen === null) {
			this.#card = 'welcome';
			return;
		}
		if (!isNewer(this.#release, seen)) return;
		this.#news = unseenNews(RELEASE_NEWS, seen, this.#release);
		if (this.#news) this.#card = 'news';
		// Nothing worth telling: a patch is remembered as seen without a word
		else this.#settle();
	}

	/** Put the card away, for this release. */
	dismiss(): void {
		this.#card = null;
		this.#settle();
	}

	showNews(): void {
		this.#news = this.latestNews;
		if (this.#news) this.#card = 'news';
	}

	startTour(): void {
		this.#card = null;
		this.#settle();
		this.#route = 'review';
		this.#touring = true;
		this.#landFrom(0, 1);
	}

	endTour(): void {
		this.#touring = false;
		// The page is no longer watched, so what it last said goes stale
		this.#onPage = null;
	}

	next(): void {
		this.#landFrom(this.#stepIndex + 1, 1);
	}

	back(): void {
		this.#landFrom(this.#stepIndex - 1, -1);
	}

	/**
	 * Hear what happened to a comment field, and move on if it was awaited.
	 *
	 * Called once the page shows the result, so the step it leads to finds
	 * what it lights.
	 */
	notice(event: CommentFieldEvent): void {
		this.#countOpen(event);
		const waiting = this.step?.waitsFor;
		if (!waiting || event.kind !== 'new') return;

		if (waiting.kind === 'comment-opened') {
			if (event.type === 'opened') this.next();
			return;
		}
		this.#followComment(event.type, waiting.routes);
	}

	/** The reader chose where a comment goes; the next step shows what came of it. */
	choose(chosen: CommentRoute): void {
		this.#route = chosen;
		this.next();
	}

	/** The release a cookie from an older release says was seen, handed over to the server; null when there is none. */
	async #fromLegacyCookie(): Promise<string | null> {
		const legacy = legacySeenRelease();
		if (legacy !== null) await handOverLegacyRelease(legacy);
		return legacy;
	}

	/** Move on to what became of a comment the step was waiting to see sent, or back if it was dropped. */
	#followComment(happened: CommentFieldEvent['type'], routes: readonly CommentRoute[]): void {
		if (happened === 'added' && routes.includes('review')) {
			this.choose('review');
		} else if (happened === 'asked' && routes.includes('ask')) {
			this.choose('ask');
		} else if (happened === 'closed' && this.#openNewComments === 0) {
			// While another comment on a line is open, that one is still to be sent
			this.back();
		}
	}

	/** Remember this release as seen, so the card does not come back. */
	#settle(): void {
		writeSeenRelease(this.#release).catch(() => {
			// Not remembered this time: the card comes back with the next review
		});
	}

	#shows(step: TourStep): boolean {
		const onPage = this.#onPage;
		if (onPage !== null && !step.targets.some((target) => onPage.has(target))) return false;
		return !(step.waitsFor?.kind === 'comment-opened' && this.#openNewComments > 0);
	}

	/** The steps this tour shows, in order: those with something on the page. */
	#shownSteps(): TourStep[] {
		return this.#steps.filter((step) => this.#shows(step));
	}

	/**
	 * Land on the first step from here, going this way, that has something to
	 * show.
	 *
	 * Going back past the start turns round, so the first step shown is always
	 * one there is something to see in; going on past the end ends the tour.
	 */
	#landFrom(index: number, direction: 1 | -1): void {
		let candidate = index;
		while (candidate >= 0 && candidate < this.#steps.length && !this.#shows(this.#steps[candidate])) {
			candidate += direction;
		}
		if (candidate < 0) {
			this.#landFrom(0, 1);
			return;
		}
		if (candidate >= this.#steps.length) {
			this.#touring = false;
			return;
		}
		this.#stepId = this.#steps[candidate].id;
	}

	/** The count of comment fields on a line, after one of them said something. */
	#countOpen(event: CommentFieldEvent): void {
		if (event.kind !== 'new') return;
		this.#openNewComments = Math.max(0, this.#openNewComments + (event.type === 'opened' ? 1 : -1));
	}
}
