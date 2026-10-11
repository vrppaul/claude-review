/**
 * What a bar's buttons ask for, and why the last of it could not be done.
 *
 * Each bar keeps its own: a retake that failed is said in the bar that
 * offered it, not in every bar on the screen.
 */

import { messageOf } from '$lib/utils/errors';

export class Attempt {
	#failed = $state<string | null>(null);

	/** Why the last thing asked for could not be done; null once it was, or while nothing has failed. */
	get failed(): string | null {
		return this.#failed;
	}

	/** Do what a button asks, saying why if it could not be done; whether it was. */
	async run(act: () => Promise<unknown>): Promise<boolean> {
		this.#failed = null;
		try {
			await act();
			return true;
		} catch (error) {
			this.#failed = messageOf(error);
			return false;
		}
	}
}
