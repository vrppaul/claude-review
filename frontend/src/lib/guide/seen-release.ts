/**
 * Which release of the review this reader has already been shown.
 *
 * Kept by the server with what the review remembers about its reader, so
 * every review on the machine knows it. It used to be a cookie; one still in
 * this browser is handed over to the server once, by whoever finds it.
 */

import { keepGuide, readGuide } from '$lib/api/review-api';

const LEGACY_COOKIE = 'claude-review-seen';

/**
 * The release last seen, as the server keeps it, or null when it keeps none.
 *
 * Throws when the server cannot say: a reader who cannot be told apart from
 * a newcomer is better left unwelcomed than welcomed twice.
 */
export async function readSeenRelease(): Promise<string | null> {
	const kept = await readGuide();
	return kept.stored ? kept.record.seen_release : null;
}

export async function writeSeenRelease(release: string): Promise<void> {
	await keepGuide({ seen_release: release });
}

/** The release a cookie from before the server kept it says was seen, while this browser still has one. */
export function legacySeenRelease(): string | null {
	const prefix = `${LEGACY_COOKIE}=`;
	const found = document.cookie.split('; ').find((part) => part.startsWith(prefix));
	return found ? decodeURIComponent(found.slice(prefix.length)) : null;
}

/** Hand the release the cookie kept over to the server, and forget the cookie. */
export async function handOverLegacyRelease(release: string): Promise<void> {
	await writeSeenRelease(release);
	document.cookie = `${LEGACY_COOKIE}=; path=/; max-age=0`;
}
