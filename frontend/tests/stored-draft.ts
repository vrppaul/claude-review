/** The draft as the page keeps it in the browser's storage, for a test that writes it there by hand. */
import { storageKey } from '$lib/utils/preferences';
import { REVIEW_IDENTITY } from './diff';

/** Where the page keeps the draft of the review a test opens. */
export const DRAFT_KEY = storageKey(`draft:${REVIEW_IDENTITY}`);
/** Where releases up to 1.5 kept the one draft of every review on a port, telling them apart by title. */
export const RELEASED_DRAFT_KEY = storageKey('draft');

/** Put whatever a test says where the page keeps the draft of the review a test opens. */
export function storeDraft(kept: object): void {
	localStorage.setItem(DRAFT_KEY, JSON.stringify(kept));
}

/** Put whatever a test says where an older release kept the draft, as that release left it. */
export function storeReleasedDraft(kept: object): void {
	localStorage.setItem(RELEASED_DRAFT_KEY, JSON.stringify(kept));
}
