/**
 * What happens to the comment fields on the page, for whoever follows along.
 *
 * Plain TypeScript, not runes: nothing here is drawn, it is only passed on.
 *
 * A field says when it opens and how it goes — added, asked, or closed
 * unsent — and knows nothing of who is listening. The tour listens; nothing
 * a field does depends on it.
 */

import type { CommentFieldEvent } from "$lib/types";

type Listener = (event: CommentFieldEvent) => void;

const listeners = new Set<Listener>();

export const commentFields = {
  report(event: CommentFieldEvent) {
    for (const listener of listeners) listener(event);
  },

  /** Follow every field from now on; returns how to stop. */
  listen(listener: Listener): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
