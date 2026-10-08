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

import type {
  AgentStatus,
  CancelRequest,
  Comment,
  Composer,
  MessageRequest,
  PanelTurn,
  Progress,
  ProgressStep,
} from "$lib/types";

import { commentStore } from "$lib/stores/comments.svelte";
import { diffStore } from "$lib/stores/diff.svelte";
import { emptyComposer, loadDraft, saveDraft } from "$lib/utils/drafts";
import { IdSequence } from "$lib/utils/ids";
import { ImageAttachments } from "$lib/utils/image-attachments.svelte";
import { readChoice, readNumber, writeChoice } from "$lib/utils/preferences";
import { refusalOf } from "$lib/utils/refusal";
import { threadOnTheWire } from "$lib/utils/thread-wire";
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
// The message being written: its words and the images pasted into it. Held
// here rather than in the panel, and saved with the draft, so hiding the
// panel or reloading the page loses neither — and no image is left on the
// server with nothing on screen pointing at it.
let composerText = $state("");
const attachments = new ImageAttachments([], rememberComposer);
const messageIds = new IdSequence("panel-");
const answerIds = new IdSequence("answer-");
const eventIds = new IdSequence("event-");

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

function remember(): void {
  if (!diffStore.title) return;
  saveDraft({ title: diffStore.title, panel: turns });
}

function rememberComposer(): void {
  if (!diffStore.title) return;
  const composer: Composer = {
    text: composerText,
    images: $state.snapshot(attachments.images),
  };
  saveDraft({ title: diffStore.title, composer });
}

/**
 * Take a message that never reached the agent off the conversation.
 *
 * The work it put out of sight comes back, unless news of other work has
 * arrived since.
 */
function takeBack(id: string, progressBefore: Progress | null): void {
  turns = turns.filter((turn) => turn.id !== id);
  if (progress === null) progress = progressBefore;
  remember();
}

function markCancelled(messageId: string, cancelled: boolean): void {
  turns = turns.map((turn) =>
    turn.id === messageId ? { ...turn, cancelled } : turn,
  );
  remember();
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
  get composerText(): string {
    return composerText;
  },
  /** The images pasted into the message being written. */
  get attachments(): ImageAttachments {
    return attachments;
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

  /** Pick the conversation, and the message half-written, up where a reload left them. */
  restore(title: string) {
    const draft = loadDraft(title);
    const saved = draft?.panel ?? [];
    turns = saved;
    const composer = draft?.composer ?? emptyComposer();
    composerText = composer.text;
    attachments.reset(composer.images);
    // Past the highest id already handed out, so an answer cannot land under
    // a message that only shares its number
    const savedIds = saved.map((turn) => turn.id);
    messageIds.continuePast(savedIds);
    answerIds.continuePast(savedIds);
    eventIds.continuePast(savedIds);
  },

  setComposerText(text: string) {
    composerText = text;
    rememberComposer();
  },

  /**
   * Send the message being written, and go on reading.
   *
   * The threads travel with the message rather than only their ids: they
   * are unsent work, held in this browser, and the server has never seen
   * them. Images are the other way round: the server already keeps them,
   * so only their ids go.
   */
  async send(threads: Comment[]): Promise<void> {
    const written = composerText;
    const text = written.trim();
    const images = $state.snapshot(attachments.images);
    const id = messageIds.next();
    turns = [
      ...turns,
      {
        id,
        author: "reader",
        body: text,
        at: Date.now(),
        threads: threads.map((thread) => thread.id),
        images,
      },
    ];
    // A new question, so whatever was being done for the last one is history
    const progressBefore = progress;
    progress = null;
    remember();

    let response: Response;
    try {
      const request: MessageRequest = {
        message_id: id,
        text,
        threads: threads.map(threadOnTheWire),
        images,
      };
      response = await fetch("/api/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
    } catch (error) {
      takeBack(id, progressBefore);
      throw error;
    }

    if (!response.ok) {
      takeBack(id, progressBefore);
      throw new Error(await refusalOf(response, "Could not send"));
    }

    // What was written or pasted while this was on its way belongs to the
    // next message, so only what went is cleared
    if (composerText.startsWith(written)) {
      composerText = composerText.slice(written.length).trimStart();
    }
    attachments.release(images);
  },

  /**
   * Say what is being done, replacing whatever was being said before.
   *
   * Whole every time: this is the state of the work, and a state that
   * arrives in pieces is a log with extra steps. Naming a message is what
   * lets the answer to it put the line out; work for no message is the
   * agent's own, and only an empty one ends that.
   */
  reportProgress(
    messageId: string | undefined,
    text: string,
    files: string[],
    steps: ProgressStep[] = [],
  ) {
    progress =
      text.trim() === "" && steps.length === 0
        ? null
        : { messageId, text, files, steps, at: Date.now() };
  },

  /** Take what was said and put it under what it answers, if anything. */
  receive(messageId: string | undefined, text: string, files: string[] = []) {
    // An answer ends the work it answers, and nothing else. Work for another
    // message, or for none — a round being worked through, agents still
    // reading — carries on, and saying so is the only way the reader sees it.
    if (
      progress &&
      progress.messageId !== undefined &&
      progress.messageId === messageId
    ) {
      progress = null;
    }
    turns = [
      ...turns,
      {
        id: answerIds.next(),
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
        id: eventIds.next(),
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
    markCancelled(messageId, true);

    let response: Response;
    try {
      const request: CancelRequest = { message_id: messageId };
      response = await fetch("/api/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
    } catch (error) {
      markCancelled(messageId, false);
      throw error;
    }

    if (!response.ok) {
      // Never heard, so the agent is still on it and the panel still waits
      markCancelled(messageId, false);
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
    composerText = "";
    attachments.reset([]);
    messageIds.reset();
    answerIds.reset();
    eventIds.reset();
  },
};
