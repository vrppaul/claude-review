/**
 * The page: what it holds before any review is open — the reader's settings
 * and layout, the theme, the socket — and the opening of the review itself.
 */

import { readReview, takeDiff } from '$lib/api/review-api';
import type { PageConnection } from '$lib/connection/page-connection';
import { catchUp, takePush } from '$lib/page/push-handling';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { PageTheme } from '$lib/reader/page-theme.svelte';
import { ReplySound } from '$lib/reader/reply-sound';
import { Settings } from '$lib/reader/settings.svelte';
import { DraftRepository } from '$lib/drafts/draft-repository';
import type { Review } from '$lib/review/review.svelte';
import { openKeptReview } from '$lib/page/kept-review';
import { TabClaim } from '$lib/page/tab-claim';
import { messageOf } from '$lib/utils/errors';

// What the page says when the review could not be opened and nothing said why
const OPENING_FAILED = 'Could not open the review';

/** Where the page has got to with its review: waiting for another tab that has it open, too. */
export type PageState =
	| { kind: 'opening' }
	| { kind: 'elsewhere' }
	| { kind: 'open'; review: Review }
	| { kind: 'failed'; reason: string };

export class ReviewPage {
	readonly #connection: PageConnection;
	readonly #claim: TabClaim;
	readonly #settings = new Settings();
	readonly #layout = new PageLayout();
	readonly #theme = new PageTheme(this.#settings);
	readonly #drafts = new DraftRepository();
	#state = $state<PageState>({ kind: 'opening' });

	/**
	 * @param connection the page's socket
	 * @param claim how this tab comes to hold the review, which one tab holds at a time
	 */
	constructor(connection: PageConnection, claim = new TabClaim(navigator.locks)) {
		this.#connection = connection;
		this.#claim = claim;
	}

	get state(): PageState {
		return this.#state;
	}

	/**
	 * Open the review this page was served for, and keep it open.
	 *
	 * Nothing happens before this tab holds the review: while another tab
	 * has it open, the page says so and waits for that tab to close. Then
	 * the socket opens first: holding it is what tells the server the review
	 * is on screen, and reading the review may take longer than the server
	 * waits for a reloaded page to come back. The reader's settings come
	 * before the diff: whether whitespace counts decides which diff is asked
	 * for. The facts come before the diff too: they say how far the telling
	 * had got, and a diff read after them holds everything told by then.
	 * Once the review is open, the socket goes on from where its draft or its
	 * facts left the telling, so whatever was said meanwhile is handed over
	 * rather than missed.
	 */
	async open(): Promise<void> {
		this.#theme.start();
		await this.#claim.claim(() => this.#waitForTheOtherTab());
		this.#state = { kind: 'opening' };
		this.#connection.open();
		try {
			await this.#settings.load();
			const facts = await readReview();
			const firstDiff = await takeDiff({
				ignoreWhitespace: this.#settings.current.ignore_whitespace,
				base: null
			});
			// An unsent review of the same thing is picked up where it stopped
			const { review } = openKeptReview(
				facts,
				firstDiff,
				{ settings: this.#settings, layout: this.#layout, sound: new ReplySound(this.#settings) },
				this.#drafts
			);
			review.tellServerThrough(this.#connection);
			this.#connection.deliverTo({
				told: () => review.telling.heard,
				take: (push, at) => takePush(review, push, at),
				catchUp: (from) => catchUp(review, from)
			});
			this.#state = { kind: 'open', review };
			// A first review is welcomed; a newer release says what changed
			void review.guide.open();
		} catch (error) {
			this.#state = {
				kind: 'failed',
				reason: messageOf(error, OPENING_FAILED)
			};
		}
	}

	#waitForTheOtherTab(): void {
		this.#state = { kind: 'elsewhere' };
	}
}
