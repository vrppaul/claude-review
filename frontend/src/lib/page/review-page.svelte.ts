/**
 * The page: what it holds before any review is open — the reader's settings
 * and layout, the theme, the socket — the opening of the review itself, and
 * letting it go once it is over.
 */

import { readConversation, readHeldThreads, readReview, takeDiff } from '$lib/api/review-api';
import type { PageConnection } from '$lib/connection/page-connection';
import { catchUp, followKeptThreads, takePush } from '$lib/page/push-handling';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { PageTheme } from '$lib/reader/page-theme.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import type { Review } from '$lib/review/review.svelte';
import { openKeptReview } from '$lib/page/kept-review';
import { messageOf } from '$lib/utils/errors';
import { stopsTogether } from '$lib/utils/stops';

/** Where the page has got to with its review. */
export type PageState = { kind: 'opening' } | { kind: 'open'; review: Review } | { kind: 'failed'; reason: string };

export class ReviewPage {
	readonly #connection: PageConnection;
	// How the page shuts its tab once the review is over; a browser lets it only for a tab a script opened
	readonly #closeTab: () => void;
	readonly #settings = new Settings();
	readonly #layout = new PageLayout();
	readonly #theme = new PageTheme(this.#settings);
	#state = $state.raw<PageState>({ kind: 'opening' });
	// How to let go of the review open now: stop telling the server what it
	// holds, stop keeping its draft, and stop asking before the tab leaves it
	#letGo: (() => void) | null = null;

	/** @param closeTab how the tab is closed once the review is over */
	constructor(connection: PageConnection, closeTab: () => void) {
		this.#connection = connection;
		this.#closeTab = closeTab;
	}

	get state(): PageState {
		return this.#state;
	}

	/**
	 * Open the review this page was served for, and keep it open.
	 *
	 * The socket opens first: holding it is what tells the server the review
	 * is on screen, and reading the review may take longer than the server
	 * waits for a reloaded page to come back. The reader's settings come
	 * before the diff: whether whitespace counts decides which diff is asked
	 * for. The facts come before the diff too: they say how far the telling
	 * had got, and a diff read after them holds everything told by then.
	 * The threads the review holds, and what was said in its panel, are read
	 * after the facts too: a thread the agent raises, or words it says, in
	 * between are then held and pushed both, and taken in once, where read
	 * before them they would be neither. Once the review is
	 * open, the socket goes on from where its draft or its facts left the
	 * telling, so whatever was said meanwhile is handed over rather than
	 * missed, and the threads its draft brought back follow onto the diff it
	 * opened on.
	 */
	async open(): Promise<void> {
		this.#theme.start();
		this.#connection.open();
		try {
			await this.#settings.load();
			const facts = await readReview();
			const [firstDiff, { threads: held }, { said }] = await Promise.all([
				takeDiff({ ignoreWhitespace: this.#settings.current.ignore_whitespace, base: null }),
				readHeldThreads(),
				readConversation()
			]);
			// An unsent review of the same thing is picked up where it stopped
			const { review, stopKeeping } = openKeptReview(
				{ facts, firstDiff, held, said },
				{ settings: this.#settings, layout: this.#layout, sound: new ReplySound(this.#settings), theme: this.#theme }
			);
			window.addEventListener('beforeunload', this.#askBeforeLeaving);
			this.#letGo = stopsTogether(review.tellServerThrough(this.#connection), stopKeeping, () =>
				window.removeEventListener('beforeunload', this.#askBeforeLeaving)
			);
			this.#connection.deliverTo({
				identity: review.identity,
				told: () => review.telling.heard,
				take: (push, at) => takePush(review, push, at),
				catchUp: (from) => catchUp(review, from),
				reached: () => review.link.reached(),
				lost: () => review.link.lost(),
				strayed: () => review.link.end('replaced')
			});
			this.#state = { kind: 'open', review };
			void followKeptThreads(review);
			// However it ended, the page lets go; the tab it was sent from shuts too
			void review.link.ended.then(() => this.close());
			void review.submission.over.then(() => this.#closeTab());
			// A first review is welcomed; a newer release says what changed
			void review.guide.open();
		} catch (error) {
			this.#state = {
				kind: 'failed',
				reason: messageOf(error)
			};
		}
	}

	/**
	 * Let go of the review: nothing more is said to the server or heard from
	 * it, and nothing more of its draft is kept once what was waiting to be
	 * kept is. Done once the review is over, for the socket would otherwise
	 * come back to whatever runs next on this port — the next review of the
	 * same repository, as like as not — and hold it open after its own page
	 * has closed. The page itself stays on screen as it is.
	 */
	close(): void {
		this.#letGo?.();
		this.#letGo = null;
		this.#connection.close();
	}

	// The browser asks the reader before the tab leaves a review with something
	// unsent in it — a link followed, the tab closed, a reload: the draft keeps
	// it, but leaving ends the review a moment later and lets its agent go
	readonly #askBeforeLeaving = (event: Event): void => {
		if (this.#state.kind === 'open' && this.#state.review.submission.hasUnsent) event.preventDefault();
	};
}
