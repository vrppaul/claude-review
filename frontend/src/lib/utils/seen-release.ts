/**
 * Which release of the review this reader has already been shown.
 *
 * Kept by the server with what the review remembers about its reader, so
 * every review on the machine knows it. It used to be a cookie; one still in
 * this browser is handed over once.
 */

import { keepGuide, readGuide } from '$lib/api/review-api';

const LEGACY_COOKIE = 'claude-review-seen';

// The numbered part of a Python release: 1.5.0 out of 1.5.0rc1 or 1.4.3.dev0
const RELEASE_NUMBERS = /^\d+(?:\.\d+)*/;

function legacyCookie(): string | null {
	const prefix = `${LEGACY_COOKIE}=`;
	const found = document.cookie.split('; ').find((part) => part.startsWith(prefix));
	return found ? decodeURIComponent(found.slice(prefix.length)) : null;
}

function forgetLegacyCookie(): void {
	document.cookie = `${LEGACY_COOKIE}=; path=/; max-age=0`;
}

/**
 * The release last seen, or null for somebody who has never opened a review.
 *
 * Throws when the server cannot say: a reader who cannot be told apart from
 * a newcomer is better left unwelcomed than welcomed twice.
 */
export async function readSeenRelease(): Promise<string | null> {
	const kept = await readGuide();
	if (kept.stored) return kept.record.seen_release;

	const handedOver = legacyCookie();
	if (handedOver === null) return null;
	await writeSeenRelease(handedOver);
	forgetLegacyCookie();
	return handedOver;
}

export async function writeSeenRelease(release: string): Promise<void> {
	await keepGuide({ seen_release: release });
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
