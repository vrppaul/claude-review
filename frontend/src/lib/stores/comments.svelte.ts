import type {
  Comment,
  CommentPayload,
  CommentSeverity,
  DiffFile,
  LineSide,
  SubmitResponse,
  Turn,
  TurnAuthor,
} from "$lib/types";
import { SvelteMap } from "svelte/reactivity";

import { reviewStore } from "$lib/stores/review.svelte";
import { reanchor } from "$lib/utils/reanchor";
import { clearDraft, loadDraft, saveDraft } from "$lib/utils/drafts";

let comments = $state<Comment[]>([]);
let reviewBody = $state("");
let submitted = $state(false);

let nextId = 0;
let nextTurnId = 0;
// What the draft is tied to, so it is not restored onto another review
let draftTitle = $state<string | null>(null);
// Where the reader is in the list, shared by every control that steps it
let cursor = $state(-1);
// Which threads have gone out, and in which round. A round carries what is
// new since the last one, not the whole review again — and the reader can
// see which of what is on screen the answering side has already read.
const sent = new SvelteMap<string, number>();

function generateId(): string {
  return `comment-${++nextId}`;
}

function generateTurnId(): string {
  return `turn-${++nextTurnId}`;
}

function idNumber(id: string): number {
  const parsed = Number.parseInt(id.replace("comment-", ""), 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function remember(): void {
  if (draftTitle === null) return;
  saveDraft({ title: draftTitle, comments, reviewBody, sent: [...sent] });
}

function replace(id: string, change: (comment: Comment) => Comment): void {
  comments = comments.map((c) => (c.id === id ? change(c) : c));
  remember();
}

/** A thread the reader has touched since the last round was sent. */
function isUnsent(comment: Comment): boolean {
  return !sent.has(comment.id);
}

function payload(comment: Comment): CommentPayload {
  return {
    file: comment.file,
    side: comment.side,
    severity: comment.severity,
    start_line: comment.start_line,
    end_line: comment.end_line,
    body: comment.body,
    // The clock belongs to reading the thread, not to what it says
    turns: comment.turns.map(({ author, body, round }) => ({
      author,
      body,
      round,
    })),
    raised_by: comment.raised_by,
    resolved: comment.resolved,
    outdated: comment.outdated,
    quote: comment.quote,
  };
}

export const commentStore = {
  get comments() {
    return comments;
  },
  get count() {
    return comments.length;
  },
  get reviewBody() {
    return reviewBody;
  },
  get hasContent() {
    return comments.length > 0 || reviewBody.trim().length > 0;
  },
  /** Whether there is anything the answering side has not been told yet. */
  get hasUnsent() {
    return comments.some(isUnsent) || reviewBody.trim().length > 0;
  },
  get submitted() {
    return submitted;
  },
  /** Threads carrying an answer nobody has looked at. */
  get unread(): Comment[] {
    return comments.filter((c) => c.unread);
  },
  get unreadCount(): number {
    return comments.filter((c) => c.unread).length;
  },
  /** Threads that have been discussed, newest answer first. */
  get answered(): Comment[] {
    return comments.filter((c) => c.turns.length > 0);
  },

  /** Step to the next or previous comment, and say which it is. */
  step(direction: 1 | -1): Comment | undefined {
    if (comments.length === 0) return undefined;
    cursor = (cursor + direction + comments.length) % comments.length;
    return comments[cursor];
  },

  setReviewBody(text: string) {
    reviewBody = text;
    remember();
  },

  /**
   * Pick up an unsent review of the same thing, and keep saving from now on.
   *
   * Returns how many comments came back, so the reader can be told rather
   * than left to wonder where they came from.
   */
  restore(title: string): number {
    draftTitle = title;
    const draft = loadDraft(title);
    if (!draft) return 0;

    comments = draft.comments;
    reviewBody = draft.reviewBody ?? "";
    sent.clear();
    for (const [id, round] of draft.sent ?? []) sent.set(id, round);
    // Past the highest id in the draft, not past its length: deleting a
    // comment before saving would otherwise hand its id out a second time,
    // and two comments sharing an id edit and delete as one.
    nextId = comments.reduce(
      (highest, c) => Math.max(highest, idNumber(c.id)),
      0,
    );
    // Turn ids are handed out the same way, and a restored thread already
    // holds some: carrying on from zero would mint one twice
    nextTurnId = comments
      .flatMap((c) => c.turns)
      .reduce(
        (highest, turn) =>
          Math.max(highest, Number.parseInt(turn.id?.slice(5) ?? "0", 10) || 0),
        0,
      );
    return comments.length;
  },

  add(
    file: string,
    side: LineSide,
    startLine: number,
    endLine: number,
    body: string,
    severity: CommentSeverity = "note",
    quote: string[] = [],
  ) {
    const comment: Comment = {
      id: generateId(),
      file,
      side,
      severity,
      start_line: startLine,
      end_line: endLine,
      body,
      turns: [],
      raised_by: "reader",
      resolved: false,
      outdated: false,
      quote,
      awaiting: [],
      collapsed: false,
      unread: false,
      round: reviewStore.round,
      at: Date.now(),
    };
    comments = [...comments, comment];
    remember();
    return comment.id;
  },

  /**
   * Take a thread the author raised and put it on the diff.
   *
   * It arrives already sent: the reader has not written it, so it must not
   * swell "unsent" or travel back to the side that wrote it. The moment
   * they answer or edit it, it stops being sent — as any thread does — and
   * goes with the next round, so the reply arrives with what it replies to.
   */
  raise(
    id: string,
    file: string,
    side: LineSide,
    startLine: number,
    endLine: number,
    body: string,
    severity: CommentSeverity,
    quote: string[],
  ): string {
    const comment: Comment = {
      id,
      file,
      side,
      severity,
      start_line: startLine,
      end_line: endLine,
      body,
      turns: [],
      raised_by: "author",
      resolved: false,
      outdated: false,
      quote,
      awaiting: [],
      collapsed: false,
      unread: true,
      round: reviewStore.round,
      at: Date.now(),
    };
    comments = [...comments, comment];
    sent.set(id, reviewStore.round);
    remember();
    return id;
  },

  update(id: string, body: string, severity?: CommentSeverity) {
    sent.delete(id);
    replace(id, (c) => ({ ...c, body, severity: severity ?? c.severity }));
  },

  remove(id: string) {
    sent.delete(id);
    comments = comments.filter((c) => c.id !== id);
    remember();
  },

  /** Add what someone said to a thread. */
  addTurn(id: string, author: TurnAuthor, body: string) {
    const turn: Turn = {
      id: generateTurnId(),
      author,
      body,
      round: reviewStore.round,
      at: Date.now(),
    };
    sent.delete(id);
    replace(id, (c) => ({ ...c, turns: [...c.turns, turn] }));
  },

  /**
   * Hand a thread over to whoever is answering, and carry on reading.
   *
   * The question is whatever was said last in the thread: the comment that
   * opened it, or the reply just written. It goes with an id and with
   * everything said before it, so an answer to the second question does not
   * arrive as an answer to the third — and does not have to guess what the
   * thread was about.
   */
  async ask(id: string) {
    const comment = comments.find((c) => c.id === id);
    if (!comment) return;

    const last = comment.turns.at(-1);
    const asksLastTurn = last?.author === "reader";
    // The comment that opened the thread is a turn like any other, and the
    // first thing whoever answers needs to read — named by whoever wrote it,
    // or an agent reading the history is handed its own words as the
    // reader's instruction.
    const opening: Turn = {
      id: comment.id,
      author: comment.raised_by,
      body: comment.body,
      round: comment.round,
    };
    const questionId = asksLastTurn ? (last.id ?? comment.id) : comment.id;
    const question = asksLastTurn ? last.body : comment.body;
    const history = asksLastTurn
      ? [opening, ...comment.turns.slice(0, -1)]
      : comment.turns;

    replace(id, (c) => ({
      ...c,
      awaiting: [...c.awaiting, { id: questionId, at: Date.now() }],
    }));

    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: comment.id,
        question_id: questionId,
        file: comment.file,
        side: comment.side,
        start_line: comment.start_line,
        end_line: comment.end_line,
        quote: comment.quote,
        body: question,
        history: history.map(({ author, body, round }) => ({
          author,
          body,
          round,
        })),
      }),
    });

    if (!response.ok) {
      replace(id, (c) => ({
        ...c,
        awaiting: c.awaiting.filter((w) => w.id !== questionId),
      }));
      throw new Error(`Could not ask: ${response.status}`);
    }
  },

  /**
   * Take an answer that came back and put it under the question it answers.
   *
   * An answerer that names the question is believed; one that does not gets
   * the oldest question still waiting, which is the order they were handed
   * over in.
   */
  receiveReply(id: string, text: string, questionId?: string) {
    const comment = comments.find((c) => c.id === id);
    if (!comment) return;

    const answers = questionId ?? comment.awaiting[0]?.id;
    const turn: Turn = {
      id: generateTurnId(),
      author: "author",
      body: text,
      round: reviewStore.round,
      at: Date.now(),
      answers,
    };
    // Not marked unsent: the answer came from the side that reads the rounds,
    // so sending it back would only repeat what they wrote
    replace(id, (c) => ({
      ...c,
      turns: [...c.turns, turn],
      awaiting: c.awaiting.filter((w) => w.id !== answers),
      unread: true,
    }));
  },

  markRead(id: string) {
    if (!comments.some((c) => c.id === id && c.unread)) return;
    replace(id, (c) => ({ ...c, unread: false }));
  },

  markAllRead() {
    comments = comments.map((c) => (c.unread ? { ...c, unread: false } : c));
    remember();
  },

  setResolved(id: string, resolved: boolean) {
    sent.delete(id);
    replace(id, (c) => ({ ...c, resolved }));
  },

  /** Fold a thread away, or bring it back. Not a state the review carries. */
  setCollapsed(id: string, collapsed: boolean) {
    replace(id, (c) => ({ ...c, collapsed }));
  },

  /** Which round a thread went out in, or nothing if it has not yet. */
  sentInRound(id: string): number | undefined {
    return sent.get(id);
  },

  /** How much of what is on screen the answering side has not seen. */
  get unsentCount(): number {
    return comments.filter(isUnsent).length;
  },

  /**
   * Move every thread onto the diff as it now stands.
   *
   * Called after a round is answered and the diff retaken: a thread whose
   * lines survived follows them, and one whose lines are gone is marked
   * rather than left pointing at a line that has become something else.
   *
   * Says how many did each, because that is what the reader stands to lose
   * and the only part of a retake they cannot see at a glance.
   */
  reanchorAll(files: DiffFile[]): { followed: number; outdated: number } {
    let followed = 0;
    let outdated = 0;

    comments = comments.map((comment) => {
      const moved = {
        ...comment,
        ...reanchor(
          comment,
          files.find((f) => f.path === comment.file)?.hunks ?? null,
        ),
      };
      if (moved.outdated && !comment.outdated) outdated += 1;
      else if (moved.start_line !== comment.start_line) followed += 1;
      return moved;
    });

    remember();
    return { followed, outdated };
  },

  getForFile(file: string): Comment[] {
    return comments.filter((c) => c.file === file);
  },

  /** Comments anchored to the end of their range on this exact row. */
  getForLine(file: string, side: LineSide, line: number): Comment[] {
    return comments.filter(
      (c) => c.file === file && c.side === side && c.end_line === line,
    );
  },

  clear() {
    comments = [];
    reviewBody = "";
    submitted = false;
    nextId = 0;
    cursor = -1;
    draftTitle = null;
    sent.clear();
  },

  /**
   * Send what has been written since the last time.
   *
   * `end` decides whether this is the last word: a round leaves the review
   * open, so the answers to it have somewhere to come back to.
   */
  async submit(end = true): Promise<SubmitResponse> {
    const trimmedBody = reviewBody.trim();
    const unsent = comments.filter(isUnsent);

    const response = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        comments: unsent.map(payload),
        ...(trimmedBody ? { body: trimmedBody } : {}),
        end,
      }),
    });

    if (!response.ok) {
      throw new Error(`Submit failed: ${response.status}`);
    }

    const result: SubmitResponse = await response.json();

    if (end) {
      submitted = true;
      // The review has left; keeping it would greet the next one as unsent work
      clearDraft();
      return result;
    }

    // A round is a line under what was said, not the end of it: the threads
    // stay, and only what happens next is new.
    for (const comment of unsent) sent.set(comment.id, result.round);
    reviewBody = "";
    reviewStore.setRound((result.round ?? reviewStore.round) + 1);
    remember();
    return result;
  },

  /** End a review that was being worked through in rounds. */
  async end(): Promise<void> {
    const response = await fetch("/api/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });

    if (!response.ok) {
      throw new Error(`Could not end the review: ${response.status}`);
    }

    submitted = true;
    clearDraft();
  },
};
