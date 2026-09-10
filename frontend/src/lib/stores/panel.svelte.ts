/**
 * The conversation with the agent that is answering this review.
 *
 * A thread is about one line. This is about everything else — the plan, the
 * tests, a file nobody commented on — and it reaches the same agent: the
 * process driving `claude-review wait`, which wrote the change and has the
 * repository in front of it.
 *
 * Nothing typed here waits for a round. There is one button, because "add
 * to review" has no meaning outside a thread.
 */

import type { AgentStatus, Comment, PanelTurn, Progress } from "$lib/types";

import { commentStore } from "$lib/stores/comments.svelte";
import { diffStore } from "$lib/stores/diff.svelte";
import { loadDraft, saveDraft } from "$lib/utils/drafts";
import { readChoice, readNumber, writeChoice } from "$lib/utils/preferences";
import { reviewWeight } from "$lib/utils/weight";

// What the panel may take of the window. Below the floor there is no room
// for a sentence; above the ceiling the diff — which the conversation is
// about — stops being readable.
export const MIN_WIDTH = 280;
export const MAX_WIDTH = 720;
const DEFAULT_WIDTH = 380;

const stored = readChoice<"on" | "off" | "unset">(
  "panel-open",
  ["on", "off"],
  "unset",
);

let turns = $state<PanelTurn[]>([]);
let open = $state(stored === "on");
let width = $state(
  readNumber("panel-width", {
    min: MIN_WIDTH,
    max: MAX_WIDTH,
    fallback: DEFAULT_WIDTH,
  }),
);
let agent = $state<AgentStatus>({ model: null, context: null, at: null });
// What the agent says it is doing. Ephemeral by nature: it is the state of
// the work, so it is never stored and never outlives the work itself.
let progress = $state<Progress | null>(null);
// Answers that landed while the panel was shut, so the header can say so
let unread = $state(0);
// Whether the reader has ever said whether they want the panel. Until they
// have, it opens itself when an agent turns up and stays out of the way
// otherwise: an empty panel beside a review nobody is answering is 380
// pixels of nothing.
let chosen = stored !== "unset";
let nextMessage = 0;
let nextEvent = 0;

/**
 * The message the agent is still working on.
 *
 * Only the last one: an older question answered out of order is the agent's
 * business, and two "working" lines in a conversation read as a fault.
 */
const working = $derived.by(() => {
  const last = [...turns].reverse().find((turn) => turn.author === "reader");
  if (!last || last.cancelled) return undefined;
  return turns.some((turn) => turn.answers === last.id) ? undefined : last;
});

/** The largest number already handed out under a prefix. */
function highest(saved: PanelTurn[], prefix: string): number {
  return saved.reduce(
    (largest, turn) =>
      turn.id.startsWith(prefix)
        ? Math.max(
            largest,
            Number.parseInt(turn.id.slice(prefix.length), 10) || 0,
          )
        : largest,
    0,
  );
}

function remember(): void {
  if (!diffStore.title) return;
  saveDraft({ title: diffStore.title, panel: turns });
}

/** The thread as whoever answers is told about it, quote and turns and all. */
function wire(comment: Comment) {
  return {
    thread_id: comment.id,
    file: comment.file,
    side: comment.side,
    start_line: comment.start_line,
    end_line: comment.end_line,
    quote: comment.quote,
    body: comment.body,
    history: comment.turns.map(({ author, body, round }) => ({
      author,
      body,
      round,
    })),
  };
}

export const panelStore = {
  get turns(): PanelTurn[] {
    return turns;
  },
  get open(): boolean {
    return open;
  },
  get width(): number {
    return width;
  },
  get agent(): AgentStatus {
    return agent;
  },
  get unread(): number {
    return unread;
  },
  get working(): PanelTurn | undefined {
    return working;
  },
  get progress(): Progress | null {
    return progress;
  },
  /** What handing this review over costs, as far as this side can tell. */
  get weight(): number {
    return reviewWeight(diffStore.files, commentStore.comments);
  },

  setOpen(next: boolean) {
    open = next;
    chosen = true;
    writeChoice("panel-open", next);
    if (next) unread = 0;
  },

  toggle() {
    this.setOpen(!open);
  },

  /** An agent has turned up; show the panel unless the reader shut it. */
  offer() {
    if (!chosen) open = true;
  },

  setWidth(next: number) {
    width = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(next)));
    writeChoice("panel-width", width);
  },

  /** Pick the conversation up where a reload left it. */
  restore(title: string) {
    const saved = loadDraft(title)?.panel ?? [];
    turns = saved;
    // Past the highest id already handed out, so an answer cannot land under
    // a message that only shares its number
    nextMessage = highest(saved, "panel-");
    nextEvent = Math.max(highest(saved, "answer-"), highest(saved, "event-"));
  },

  /**
   * Say something to the agent, and go on reading.
   *
   * The threads travel with the message rather than only their ids: they
   * are unsent work, held in this browser, and the server has never seen
   * them.
   */
  async send(text: string, threads: Comment[]): Promise<void> {
    const id = `panel-${++nextMessage}`;
    turns = [
      ...turns,
      {
        id,
        author: "reader",
        body: text,
        at: Date.now(),
        threads: threads.map((thread) => thread.id),
      },
    ];
    // A new question, so whatever was being done for the last one is history
    progress = null;
    remember();

    const response = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: id,
        text,
        threads: threads.map(wire),
      }),
    });

    if (!response.ok) {
      turns = turns.filter((turn) => turn.id !== id);
      remember();
      throw new Error(`Could not send: ${response.status}`);
    }
  },

  /** Say what is being done, replacing whatever was being said before. */
  reportProgress(text: string, files: string[]) {
    progress = text.trim() === "" ? null : { text, files, at: Date.now() };
  },

  /** Take what was said and put it under what it answers, if anything. */
  receive(messageId: string | undefined, text: string, files: string[] = []) {
    // Something was said, so whatever was being done is done
    progress = null;
    turns = [
      ...turns,
      {
        id: `answer-${++nextEvent}`,
        author: "author",
        body: text,
        at: Date.now(),
        answers: messageId,
        files,
      },
    ];
    if (!open) unread += 1;
    remember();
  },

  /**
   * Note something the review itself did, between what was said about it.
   *
   * A retaken diff is not a turn — nobody said it — but it happened in the
   * middle of the conversation, and an answer written before it was written
   * about different code.
   */
  note(body: string, threads: string[] = []) {
    turns = [
      ...turns,
      {
        id: `event-${++nextEvent}`,
        author: "event",
        body,
        at: Date.now(),
        threads,
      },
    ];
    remember();
  },

  /**
   * Take a message back before it is answered.
   *
   * A request, not a kill: the agent is in another process and decides what
   * to do about it. The panel stops waiting either way, because the reader
   * has said they are no longer interested.
   */
  async cancel(messageId: string): Promise<void> {
    turns = turns.map((turn) =>
      turn.id === messageId ? { ...turn, cancelled: true } : turn,
    );
    remember();

    const response = await fetch("/api/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId }),
    });

    if (!response.ok) {
      throw new Error(`Could not stop it: ${response.status}`);
    }
  },

  /** What the agent says about itself, quoted with the time it said it. */
  report(reported: AgentStatus) {
    agent = reported;
  },

  clear() {
    turns = [];
    progress = null;
    agent = { model: null, context: null, at: null };
    unread = 0;
    nextMessage = 0;
    nextEvent = 0;
  },
};
