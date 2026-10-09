/**
 * How many files have changed on disk since the diff on screen was taken.
 *
 * Said, never acted on: swapping the diff under a half-written comment
 * would orphan it, so the reader decides when to take it again.
 */
export class TreeMoved {
	// Zero means there is nothing to say: nothing has moved, or the reader has
	// dismissed it until something does
	#count = $state(0);
	// What the reader has already waved away. The tree does not move back, so
	// the same number arriving again — on a reload, or with the next diff — is
	// the same news they have already dismissed.
	#dismissed = 0;

	/** How many files have moved on since this diff was taken, if still worth saying. */
	get count(): number {
		return this.#count;
	}

	/** The server counted the files that moved: with a diff, or pushed as it happened. */
	note(count: number): void {
		this.#count = count === this.#dismissed ? 0 : count;
	}

	/** Dismissed until the tree moves again, so a long edit does not nag. */
	dismiss(): void {
		this.#dismissed = this.#count;
		this.#count = 0;
	}

	/** A diff was taken again: whatever moved is in it now. */
	settle(): void {
		this.#count = 0;
		this.#dismissed = 0;
	}
}
