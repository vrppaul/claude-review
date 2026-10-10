/**
 * The review is open in one tab at a time.
 *
 * A tab keeps its draft in the one place drafts are kept, and tells the
 * server the threads it holds. Two tabs on one review would each do both,
 * and whichever spoke last would win: the other's work would be written
 * over. So the first tab to open the review holds it for as long as it is
 * open, and a second waits — saying so — until the first is closed, then
 * opens the review from the draft the first one kept.
 */

import { storageKey } from '$lib/utils/preferences';

// The lock held by the tab the review is open in
const OPEN_HERE = storageKey('open-here');
// Held until the page goes: the browser lets go of a tab's locks with the tab
const HELD_WHILE_THE_PAGE_LIVES: Promise<never> = new Promise(() => undefined);

/** What is done once a lock is granted, or found taken. */
type Granted = (lock: Lock | null) => Promise<never> | undefined;

/** The part of the browser's lock manager a claim needs. */
export interface Locks {
	request(name: string, options: LockOptions, granted: Granted): Promise<unknown>;
}

export class TabClaim {
	readonly #locks: Locks | undefined;
	#whileElsewhere: () => void = () => undefined;
	#claimed: () => void = () => undefined;

	/** @param locks the browser's lock manager; absent in jsdom, and in browsers too old to matter here */
	constructor(locks: Locks | undefined) {
		this.#locks = locks;
	}

	/**
	 * Hold the review in this tab: at once, or — once `whileElsewhere` is told
	 * that another tab has it open — when that tab is closed. Without locks,
	 * every tab holds it.
	 */
	claim(whileElsewhere: () => void): Promise<void> {
		if (this.#locks === undefined) return Promise.resolve();
		this.#whileElsewhere = whileElsewhere;
		const claimed = new Promise<void>((resolve) => (this.#claimed = resolve));
		void this.#locks.request(OPEN_HERE, { ifAvailable: true }, this.#tried);
		return claimed;
	}

	readonly #tried = (lock: Lock | null): Promise<never> | undefined => {
		if (lock !== null) return this.#held();
		this.#whileElsewhere();
		void this.#locks?.request(OPEN_HERE, {}, this.#held);
		return undefined;
	};

	readonly #held = (): Promise<never> => {
		this.#claimed();
		return HELD_WHILE_THE_PAGE_LIVES;
	};
}
