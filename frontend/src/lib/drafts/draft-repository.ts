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
// Held while a tab reads the kept draft and writes it back, so tabs keeping
// theirs at the same moment take turns rather than write over each other
const DRAFT_LOCK = storageKey('draft-lock');

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
	 * Read the draft and write it back with no other tab's reading and
	 * writing in between, so what is kept after is built on what was kept
	 * before. At once where the browser holds no locks.
	 */
	async inTurn(task: () => void): Promise<void> {
		// Absent in jsdom, and in browsers too old to matter here
		if (typeof navigator.locks === 'undefined') {
			task();
			return;
		}
		await navigator.locks.request(DRAFT_LOCK, task);
	}

	/**
	 * Hear when another tab on the same review keeps its draft. A tab is
	 * never told of its own writes, only of the others'. Returns how to stop.
	 */
	onChange(title: string, listener: () => void): () => void {
		const heard = (event: StorageEvent) => this.#heard(event, title, listener);
		window.addEventListener('storage', heard);
		return () => window.removeEventListener('storage', heard);
	}

	#heard(event: StorageEvent, title: string, listener: () => void): void {
		if (event.key === DRAFT_KEY && draftOf(event.newValue, title) !== null) listener();
	}
}
