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
// What a kept draft that cannot be read is set aside under, beside the key
// it was kept under, numbered from the first: kept as it was, for a release
// that reads it, and never written over by a later one
const SET_ASIDE = ':unreadable:';
const FIRST_SET_ASIDE = 1;

/** What the browser kept of a review's draft: the draft, if one could be read, and whether one that could not was set aside. */
export interface KeptDraft {
	draft: Draft | null;
	setAside: boolean;
}

const NOTHING_KEPT: KeptDraft = { draft: null, setAside: false };

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

/** The first place beside a key that nothing set aside from it holds yet. */
function setAsideKeyOf(key: string): string {
	let number = FIRST_SET_ASIDE;
	while (localStorage.getItem(`${key}${SET_ASIDE}${String(number)}`) !== null) number += 1;
	return `${key}${SET_ASIDE}${String(number)}`;
}

/**
 * Put what was kept under a key aside, as it was, under a key of its own
 * beside it; say whether it could be. Taken from where it was, it neither
 * stops the next page from opening nor is written over by the next save.
 */
function setAside(key: string): boolean {
	try {
		const kept = localStorage.getItem(key);
		if (kept === null) return false;
		localStorage.setItem(setAsideKeyOf(key), kept);
		localStorage.removeItem(key);
		return true;
	} catch (error) {
		// Refused, it stays where it was
		if (!isStorageRefused(error)) throw error;
		return false;
	}
}

/**
 * What a draft that could not be read leaves: nothing, when it was not JSON
 * or storage was refused. Anything else is a fault in reading or bringing
 * up to date what was kept: told whole to the console, and the draft set
 * aside, so the review opens without it rather than not at all.
 */
function unreadable(key: string, error: unknown): KeptDraft {
	if (error instanceof SyntaxError || isStorageRefused(error)) return NOTHING_KEPT;
	console.error('claude-review: a kept draft could not be read, and is set aside', error);
	return { draft: null, setAside: setAside(key) };
}

/**
 * The draft of the review of this identity, in the current shape, if one
 * was kept and can be read. A draft an older release kept under the
 * review's title is picked up by the first review of that title to open.
 */
export function readDraft(identity: string, title: string): KeptDraft {
	const ownKey = draftKeyOf(identity);
	try {
		const kept = keptUnder(ownKey);
		if (isCurrentDraft(kept)) return { draft: kept, setAside: false };
	} catch (error) {
		return unreadable(ownKey, error);
	}
	try {
		return { draft: pickUpReleased(identity, title), setAside: false };
	} catch (error) {
		return unreadable(RELEASED_DRAFT_KEY, error);
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
