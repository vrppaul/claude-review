/**
 * Which entry of the release news a reader is shown.
 *
 * Only ever one, the newest that applies: a card that lists three releases
 * is a changelog, and the changelog is a link away. From it the reader goes
 * to the one before or after, one at a time.
 */

import type { ReleaseNews } from '$lib/guide/news';

// The numbered part of a Python release: 1.5.0 out of 1.5.0rc1 or 1.4.3.dev0
const RELEASE_NUMBERS = /^\d+(?:\.\d+)*/;

/**
 * The newest entry a returning reader has not been shown.
 *
 * After the release they last saw and no later than the one serving them.
 * Usually that is the serving release's own entry; when it has none, the
 * newest one they skipped over speaks instead of silence.
 */
export function unseenNews(entries: ReleaseNews[], seen: string, serving: string): ReleaseNews | undefined {
	return furthest(
		entries.filter((entry) => isNewer(entry.release, seen) && !isNewer(entry.release, serving)),
		isNewer
	);
}

/** The newest entry up to the serving release, to read again from the ? list. */
export function latestNews(entries: ReleaseNews[], serving: string): ReleaseNews | undefined {
	return furthest(
		entries.filter((entry) => !isNewer(entry.release, serving)),
		isNewer
	);
}

/** The news of the release before the one shown: where the card's arrow back leads. */
export function newsBefore(entries: ReleaseNews[], shown: string): ReleaseNews | undefined {
	return furthest(
		entries.filter((entry) => isOlder(entry.release, shown)),
		isNewer
	);
}

/** The news of the release after the one shown, up to the serving release: where the card's arrow forward leads. */
export function newsAfter(entries: ReleaseNews[], shown: string, serving: string): ReleaseNews | undefined {
	return furthest(
		entries.filter((entry) => isNewer(entry.release, shown) && !isNewer(entry.release, serving)),
		isOlder
	);
}

/** The entry whose release is the furthest one way: the newest by `isNewer`, the oldest by `isOlder`. */
function furthest(
	entries: ReleaseNews[],
	further: (candidate: string, than: string) => boolean
): ReleaseNews | undefined {
	return entries.reduce<ReleaseNews | undefined>(
		(found, entry) => (!found || further(entry.release, found.release) ? entry : found),
		undefined
	);
}

/** Whether one release came out before another. */
function isOlder(candidate: string, than: string): boolean {
	return isNewer(than, candidate);
}

/**
 * Whether one release came out after another.
 *
 * Numbers compared part by part, so 1.10 comes after 1.9. A pre-release or
 * a development build counts as the release it leads to: what is new is
 * written per release, and 1.5.0rc1 is about to be 1.5.0.
 */
export function isNewer(candidate: string, than: string): boolean {
	const left = releaseNumbers(candidate);
	const right = releaseNumbers(than);
	for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
		const difference = (left[index] ?? 0) - (right[index] ?? 0);
		if (difference !== 0) return difference > 0;
	}
	return false;
}

function releaseNumbers(release: string): number[] {
	const numbered = RELEASE_NUMBERS.exec(release)?.[0] ?? '';
	return numbered.split('.').map((part) => Number.parseInt(part, 10) || 0);
}
