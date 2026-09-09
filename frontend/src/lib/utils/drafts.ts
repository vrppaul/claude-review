import type { Comment } from "$lib/types";

const STORAGE_KEY = "claude-review:draft";

export interface Draft {
  /** What the review was of, so a draft is not restored onto a different one. */
  title: string;
  comments: Comment[];
  reviewBody: string;
}

/**
 * Keep a review in progress across a reload.
 *
 * Comments live only in the page until they are sent, so a stray reload, a
 * closed tab or a crash used to take an hour of reading with it. The draft is
 * tied to what was being reviewed: opening a different review does not
 * inherit it.
 */
export function saveDraft(draft: Draft): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Private windows and blocked site data both throw; the review still works
  }
}

export function loadDraft(title: string): Draft | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const draft: Draft = JSON.parse(stored);
    if (draft.title !== title || !Array.isArray(draft.comments)) return null;
    return draft;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do: the draft simply outlives the review
  }
}
