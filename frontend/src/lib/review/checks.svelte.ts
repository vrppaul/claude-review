/**
 * The checks the agent reported running on the change — its tests, linters,
 * type checkers — as the review holds them: how each ended, and whether the
 * code moved on since. The review decides all of that; the page holds what
 * it last said, whole.
 */

import type { Check } from '$lib/types';

export class Checks {
	#all: readonly Check[];

	constructor(reported: readonly Check[]) {
		this.#all = $state.raw(reported);
	}

	/** Every check the agent reported, as the review last said each stands. */
	get all(): readonly Check[] {
		return this.#all;
	}

	/** Take in the checks as the review says they stand now: every one, in place of those held. */
	take(reported: readonly Check[]): void {
		this.#all = reported;
	}
}
