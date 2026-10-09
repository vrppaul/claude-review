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

/** Where the page has got to with its review. */
export type PageState = { kind: 'opening' } | { kind: 'open'; review: Review } | { kind: 'failed'; reason: string };

export class ReviewPage {
	readonly #connection: PageConnection;
	readonly #settings = new Settings();
	readonly #layout = new PageLayout();
	readonly #theme = new PageTheme(this.#settings);
	readonly #drafts = new DraftRepository();
	#state = $state<PageState>({ kind: 'opening' });

	constructor(connection: PageConnection) {
		this.#connection = connection;
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
	 * for. Once the review is open, the socket goes on from where its draft
	 * or its facts left the telling, so whatever was said meanwhile is handed
	 * over rather than missed.
	 */
	async open(): Promise<void> {
		this.#theme.start();
		this.#connection.open();
		try {
			await this.#settings.load();
			const [facts, firstDiff] = await Promise.all([
				readReview(),
				takeDiff({
					ignoreWhitespace: this.#settings.current.ignore_whitespace,
					base: null
				})
			]);
			// An unsent review of the same thing is picked up where it stopped
			const { review } = openKeptReview(
				facts,
				firstDiff,
				{ settings: this.#settings, layout: this.#layout, sound: new ReplySound(this.#settings) },
				this.#drafts
			);
			review.tellServerThrough(this.#connection);
			this.#connection.deliverTo({
				told: () => review.telling.position,
				take: (push, at) => takePush(review, push, at),
				catchUp: (from) => catchUp(review, from)
			});
			this.#state = { kind: 'open', review };
			// A first review is welcomed; a newer release says what changed
			void review.guide.open();
		} catch (error) {
			this.#state = {
				kind: 'failed',
				reason: error instanceof Error ? error.message : 'Could not open the review'
			};
		}
	}
}
