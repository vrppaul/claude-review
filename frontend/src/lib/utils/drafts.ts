import type { Comment } from "$lib/types";

const STORAGE_KEY = "claude-review:draft";
// What shape the stored draft is in. A comment has grown turns, a resolved
// mark, the lines it was written against and the questions still waiting for
// an answer. The number is here so an older draft can be brought up to the
// current shape — never so it can be thrown away: a draft is an hour of
// somebody's reading.
const SHAPE = 4;

export interface Draft {
  version: number;
  /** What the review was of, so a draft is not restored onto a different one. */
  title: string;
  comments: Comment[];
  reviewBody: string;
  /** Threads already sent, and the round each went out in. */
  sent: [string, number][];
}

/**
 * Keep a review in progress across a reload.
 *
 * Comments live only in the page until they are sent, so a stray reload, a
 * closed tab or a crash used to take an hour of reading with it. The draft is
 * tied to what was being reviewed: opening a different review does not
 * inherit it.
 */
export function saveDraft(draft: Omit<Draft, "version">): void {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...draft, version: SHAPE }),
    );
  } catch {
    // Private windows and blocked site data both throw; the review still works
  }
}

/**
 * Bring a draft written by an older version up to the current shape.
 *
 * Every field added since has an empty value that means "this comment
 * predates it", so filling them in is enough. Dropping the draft instead
 * would be losing work to a version number.
 */
function upgrade(draft: Draft): Draft {
  return {
    ...draft,
    version: SHAPE,
    reviewBody: draft.reviewBody ?? "",
    // Before rounds were numbered a sent thread was only an id
    sent: (Array.isArray(draft.sent) ? draft.sent : []).map((entry) =>
      Array.isArray(entry) ? entry : [entry as unknown as string, 1],
    ),
    comments: draft.comments.map((comment) => ({
      ...comment,
      turns: comment.turns ?? [],
      resolved: comment.resolved ?? false,
      outdated: comment.outdated ?? false,
      quote: comment.quote ?? [],
      awaiting: comment.awaiting ?? [],
      collapsed: comment.collapsed ?? false,
      unread: comment.unread ?? false,
      round: comment.round ?? 1,
      at: comment.at ?? 0,
    })),
  };
}

export function loadDraft(title: string): Draft | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const draft: Draft = JSON.parse(stored);
    if (draft.title !== title || !Array.isArray(draft.comments)) return null;
    return draft.version === SHAPE ? draft : upgrade(draft);
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
