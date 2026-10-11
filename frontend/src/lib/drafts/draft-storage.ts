/**
 * Where an unsent review is kept across a reload: read, written and
 * forgotten here, and nowhere else.
 *
 * Comments live only in the page until they are sent, so a stray reload, a
 * closed tab or a crash used to take an hour of reading with it. Each
 * review's draft is kept under the name the review gives itself: a port is
 * one origin to the browser, and two reviews served on one port — the same
 * port named twice, or two repositories of one name — each find their own.
 */

import { type Draft, isCurrentDraft, isReleasedDraft, upToDate } from '$lib/drafts/draft-shapes';
import { storageKey } from '$lib/utils/preferences';

// Where releases up to 1.5 kept the one draft of every review on a port,
// telling them apart by title
const RELEASED_DRAFT_KEY = storageKey('draft');

/** Where the draft of the review of this identity is kept. */
function draftKeyOf(identity: string): string {
	return storageKey(`draft:${identity}`);
}

/**
 * Whether the browser refused its storage — private windows and blocked
 * site data refuse it, a full one refuses a write — rather than the page
 * failing at something of its own.
 */
function isStorageRefused(error: unknown): boolean {
	return error instanceof DOMException;
}

/** What was kept under a key, read as JSON; null for nothing. */
function keptUnder(key: string): unknown {
	const kept = localStorage.getItem(key);
	return kept === null ? null : JSON.parse(kept);
}

/**
 * The draft an older release kept for the review of this title, moved under
 * the review's own name as it is picked up: once picked up, it is that
 * review's, and no other review of the same title finds it. One kept for
 * another title is left for the review it was written in.
 */
function pickUpReleased(identity: string, title: string): Draft | null {
	const kept = keptUnder(RELEASED_DRAFT_KEY);
	if (!isReleasedDraft(kept) || kept.title !== title) return null;
	const draft = upToDate(kept);
	// Kept under the review's name before the old place is emptied, so a page
	// that goes in between loses nothing
	keepDraft(identity, draft);
	localStorage.removeItem(RELEASED_DRAFT_KEY);
	return draft;
}

/**
 * The draft of the review of this identity, in the current shape; null when
 * there is none. A draft an older release kept under the review's title is
 * picked up by the first review of that title to open.
 */
export function readDraft(identity: string, title: string): Draft | null {
	try {
		const kept = keptUnder(draftKeyOf(identity));
		if (isCurrentDraft(kept)) return kept;
		return pickUpReleased(identity, title);
	} catch (error) {
		// Not JSON, or storage refused: nothing to pick up. Anything else is a
		// fault in bringing a draft up to date, and passing it off as no draft
		// would open the review without it for good; said, the draft stays
		// where it was kept for a release that reads it.
		if (error instanceof SyntaxError || isStorageRefused(error)) return null;
		throw error;
	}
}

/** Keep the draft of the review of this identity as it now stands. */
export function keepDraft(identity: string, draft: Draft): void {
	const written = JSON.stringify(draft);
	try {
		localStorage.setItem(draftKeyOf(identity), written);
	} catch (error) {
		// Refused, the review still works without a draft kept
		if (!isStorageRefused(error)) throw error;
	}
}

/** Forget the draft of the review of this identity: it is over. */
export function forgetDraft(identity: string): void {
	try {
		localStorage.removeItem(draftKeyOf(identity));
	} catch (error) {
		// Refused, the draft simply outlives the review
		if (!isStorageRefused(error)) throw error;
	}
}
