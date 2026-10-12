/**
 * Whether something has come near enough to the reader to be built — the
 * rows of a file, of a piece of one — and stays built from then on.
 */

import { whenNearViewport } from '$lib/dom/scroll';

export class BuiltWhenNear {
	#built = $state(false);

	/** Whether it has come within reach: once it has, it is built for good. */
	get built(): boolean {
		return this.#built;
	}

	/**
	 * Watch an element come within reach of the area the review scrolls in,
	 * the page itself when null. Returns how to stop watching; nothing, once
	 * it is built.
	 */
	watch(element: HTMLElement, scrollRoot: HTMLElement | null): (() => void) | undefined {
		if (this.#built) return undefined;
		return whenNearViewport(element, scrollRoot, () => (this.#built = true));
	}
}
