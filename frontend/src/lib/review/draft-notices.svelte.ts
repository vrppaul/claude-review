/**
 * What the reader is told of the draft a review opened from, under the
 * header until they dismiss it: the unsent work it brought back, or that a
 * kept draft could not be read and was set aside.
 */
export class DraftNotices {
	// How many threads came back from the draft, so the reader is told rather
	// than left to wonder where they came from; zero once they have seen it
	#restoredCount: number;
	// Whether a kept draft could not be read and was set aside, so the reader
	// is told why their unsent work is not here; false once they have seen it
	#setAside: boolean;

	constructor(restoredCount: number, setAside: boolean) {
		this.#restoredCount = $state(restoredCount);
		this.#setAside = $state(setAside);
	}

	get restoredCount(): number {
		return this.#restoredCount;
	}

	dismissRestored(): void {
		this.#restoredCount = 0;
	}

	get setAside(): boolean {
		return this.#setAside;
	}

	dismissSetAside(): void {
		this.#setAside = false;
	}
}
