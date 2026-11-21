/**
 * The names the change touched in each file of the diff on screen, as the
 * review said them: read apart from the diff, which never waits on them,
 * and handed out only while they are of the diff on screen, the same take
 * read the same way. Names of another take or another reading are never
 * handed out under the files of this one.
 *
 * They are read once something draws them, and again whenever another
 * diff comes on screen: a reader who keeps the tree put away has no file
 * of the change parsed for them.
 */

import { readNamesTouched } from '$lib/api/review-api';
import type { DiffReading, ReviewDiff } from '$lib/review/review-diff.svelte';
import type { FileNamesTouched, LinePlace, ReviewMode, TouchedName } from '$lib/types';
import { READS_NAMES } from '$lib/review/reads-names';
import { placeOfKey } from '$lib/utils/line-places';

/** The files the review said names of, by their paths: one to a path. */
type FilesByPath = Partial<Record<string, FileNamesTouched[]>>;

/** The names read of one reading of the diff: the files that have any, by their paths, and whether there are any. */
interface NamesRead {
	reading: DiffReading;
	byPath: FilesByPath;
	any: boolean;
}

// What a file whose names are not read, or that has none, lists
const NO_NAMES: readonly TouchedName[] = [];

/** Whether a name stands on a line: among those it is defined on, on the line's side. */
function standsOn(name: TouchedName, place: LinePlace): boolean {
	return name.stands_on.some(
		(lines) => lines.side === place.side && lines.first <= place.number && place.number <= lines.last
	);
}

export class TouchedNames {
	readonly #reads: boolean;
	readonly #diff: ReviewDiff;
	#read = $state.raw<NamesRead | null>(null);
	// The reading last asked about: an answer about any other is of a diff no longer on screen
	#asked: DiffReading | null = null;

	/**
	 * @param mode the kind of review, which says whether it has names to read at all
	 * @param diff the diff on screen, whose reading the names are read of and handed out with
	 */
	constructor(mode: ReviewMode, diff: ReviewDiff) {
		this.#reads = READS_NAMES[mode];
		this.#diff = diff;
	}

	/**
	 * Read the names of the diff on screen, unless they are asked of it already: whoever draws them asks as it
	 * changes. A read that fails leaves the files without names.
	 */
	async follow(): Promise<void> {
		const reading = this.#diff.reading;
		if (!this.#reads || this.#asked === reading) return;
		this.#asked = reading;
		try {
			const said = await readNamesTouched(reading.asked);
			// Read once a retake had landed: of a take the diff on screen is not, and the new diff on its way
			if (this.#asked !== reading || said.take !== reading.take) return;
			// Grouped into an object with no prototype, where a path such as `constructor` finds only what was read of it;
			// the review lists only the files that have names
			this.#read = {
				reading,
				byPath: Object.groupBy(said.files, (file) => file.path),
				any: said.files.length > 0
			};
		} catch {
			// Nothing is drawn of names that could not be read: the files stand alone, as in a review of none
		}
	}

	/** The names the change touched in a file of the diff on screen, in the order of its diff; none while not read. */
	of(path: string): readonly TouchedName[] {
		return this.#readOnScreen?.byPath[path]?.flatMap((file) => file.names) ?? NO_NAMES;
	}

	/** Whether any file of the diff on screen has names to list. */
	get any(): boolean {
		return this.#readOnScreen?.any ?? false;
	}

	/** The name of a file that stands on any of these lines, by the keys their places are known by, where one does. */
	standingOn(path: string, lineKeys: readonly string[]): TouchedName | null {
		const places = lineKeys.map(placeOfKey).filter((place) => place !== null);
		return this.of(path).find((name) => places.some((place) => standsOn(name, place))) ?? null;
	}

	/** The names read, while they are of the diff on screen: the same take read the same way. */
	get #readOnScreen(): NamesRead | null {
		const read = this.#read;
		return read?.reading === this.#diff.reading ? read : null;
	}
}
