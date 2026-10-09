/**
 * Where an unsent review is kept across a reload: one place that reads it,
 * writes it, forgets it, and hears when another tab writes it.
 *
 * Comments live only in the page until they are sent, so a stray reload, a
 * closed tab or a crash used to take an hour of reading with it. The draft
 * is tied to what was being reviewed: opening a different review does not
 * inherit it.
 */

import { type Draft, isKeptDraft, upToDate } from '$lib/drafts/draft-shapes';
import { storageKey } from '$lib/utils/preferences';

const DRAFT_KEY = storageKey('draft');

/** A draft of this review, read from what was kept; null for none or another review's. */
function draftOf(kept: string | null, title: string): Draft | null {
	if (kept === null) return null;
	try {
		const parsed: unknown = JSON.parse(kept);
		if (!isKeptDraft(parsed) || parsed.title !== title) return null;
		return upToDate(parsed);
	} catch {
		// Not a draft this page can read: nothing to pick up
		return null;
	}
}

export class DraftRepository {
	/** The draft of this review, brought up to the current shape; null when there is none. */
	load(title: string): Draft | null {
		try {
			return draftOf(localStorage.getItem(DRAFT_KEY), title);
		} catch {
			// Private windows and blocked site data both throw: nothing was kept
			return null;
		}
	}

	/**
	 * Keep the draft as it now stands. What is already kept is not written
	 * again, so a tab that has just taken in another tab's draft does not
	 * write it back and wake that tab in turn.
	 */
	save(draft: Draft): void {
		const text = JSON.stringify(draft);
		try {
			if (localStorage.getItem(DRAFT_KEY) === text) return;
			localStorage.setItem(DRAFT_KEY, text);
		} catch {
			// Private windows and blocked site data both throw; the review still works
		}
	}

	/** Forget the draft: the review it was of has been sent. */
	clear(): void {
		try {
			localStorage.removeItem(DRAFT_KEY);
		} catch {
			// Nothing to do: the draft simply outlives the review
		}
	}

	/**
	 * Hear when another tab on the same review keeps its draft. A tab is
	 * never told of its own writes, only of the others'. Returns how to stop.
	 */
	onChange(title: string, listener: (draft: Draft) => void): () => void {
		const heard = (event: StorageEvent) => this.#heard(event, title, listener);
		window.addEventListener('storage', heard);
		return () => window.removeEventListener('storage', heard);
	}

	#heard(event: StorageEvent, title: string, listener: (draft: Draft) => void): void {
		if (event.key !== DRAFT_KEY) return;
		const draft = draftOf(event.newValue, title);
		if (draft !== null) listener(draft);
	}
}
