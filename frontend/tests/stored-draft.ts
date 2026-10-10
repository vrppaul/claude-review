/** The draft as the page keeps it in the browser's storage, for a test that writes it there by hand. */
import { storageKey } from '$lib/utils/preferences';

/** Where the page keeps the draft between reloads. */
export const DRAFT_KEY = storageKey('draft');

/** Put whatever a test says into the place the draft is kept, as a page — of this release or an older one — left it. */
export function storeDraft(kept: object): void {
	localStorage.setItem(DRAFT_KEY, JSON.stringify(kept));
}
