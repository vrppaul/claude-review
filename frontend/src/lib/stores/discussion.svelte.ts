import { SvelteMap } from "svelte/reactivity";

import type { Comment } from "$lib/types";

export interface ThreadTalk {
  asked: string;
  answer: string | null;
}

/**
 * Questions asked about a comment thread, and the answers that came back.
 *
 * Asking does not block: the question is left for whoever is answering, the
 * reader carries on, and the answer is pushed into the thread when it
 * arrives. That is why an unanswered question is a state worth showing.
 */
const talk = new SvelteMap<string, ThreadTalk>();

export const discussionStore = {
  forThread(threadId: string): ThreadTalk | undefined {
    return talk.get(threadId);
  },

  async ask(comment: Comment, quote: string[], question: string) {
    talk.set(comment.id, { asked: question, answer: null });

    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: comment.id,
        file: comment.file,
        side: comment.side,
        start_line: comment.start_line,
        end_line: comment.end_line,
        quote,
        body: question,
      }),
    });

    if (!response.ok) {
      talk.delete(comment.id);
      throw new Error(`Could not ask: ${response.status}`);
    }
  },

  receive(threadId: string, text: string) {
    const existing = talk.get(threadId);
    talk.set(threadId, { asked: existing?.asked ?? "", answer: text });
  },

  clear() {
    talk.clear();
  },
};
