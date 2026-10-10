/** The one lock a page claims its review with, held by another tab until the test closes it. */
import type { Locks } from '$lib/page/tab-claim';

type Granted = Parameters<Locks['request']>[2];

export class AnotherTabHolding implements Locks {
	#heldElsewhere = true;
	#waiting: Granted | null = null;

	request(name: string, options: LockOptions, granted: Granted): Promise<unknown> {
		if (!this.#heldElsewhere) void granted({ name, mode: 'exclusive' });
		else if (options.ifAvailable) void granted(null);
		else this.#waiting = granted;
		return Promise.resolve();
	}

	/** The other tab is closed, and the page waiting is granted the lock. */
	closeTheOtherTab(): void {
		this.#heldElsewhere = false;
		void this.#waiting?.({ name: 'claimed', mode: 'exclusive' });
	}
}
