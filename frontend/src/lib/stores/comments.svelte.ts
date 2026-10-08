import type {
  Anchor,
  AskRequest,
  Comment,
  CommentSeverity,
  FollowOutcome,
  FollowRequest,
  FollowResponse,
  NewComment,
  NewTurn,
  SubmitRequest,
  SubmitResponse,
  Turn,
} from "$lib/types";
import { SvelteMap } from "svelte/reactivity";

import { anchorPlace } from "$lib/anchors/views";
import { reviewStore } from "$lib/stores/review.svelte";
import { threadOnTheWire } from "$lib/utils/thread-wire";
import { tellServer } from "$lib/stores/session.svelte";
import { clearDraft, loadDraft, saveDraft } from "$lib/utils/drafts";
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from "$lib/utils/ids";

let comments = $state<Comment[]>([]);
let reviewBody = $state("");
let submitted = $state(false);

const commentIds = new IdSequence(COMMENT_ID_PREFIX);
const turnIds = new IdSequence(TURN_ID_PREFIX);
// What the draft is tied to, so it is not restored onto another review
let draftTitle = $state<string | null>(null);
// Where the reader is in the list, shared by every control that steps it
let cursor = $state(-1);
// Which threads have gone out, and in which round. A round carries what is
// new since the last one, not the whole review again — and the reader can
// see which of what is on screen the answering side has already read.
const sent = new SvelteMap<string, number>();

function remember(): void {
  if (draftTitle === null) return;
  saveDraft({
    title: draftTitle,
    comments,
    reviewBody,
    sent: [...sent],
    issued: { comments: commentIds.issued, turns: turnIds.issued },
  });
  // The threads are unsent work and live only here. An agent that attaches
  // later has no other way to learn they exist, so the server is kept up to
  // date — it costs nothing until somebody asks it for them.
  tellServer();
}

function replace(id: string, change: (comment: Comment) => Comment): void {
  comments = comments.map((c) => (c.id === id ? change(c) : c));
  remember();
}

/** A thread the reader has touched since the last round was sent. */
function isUnsent(comment: Comment): boolean {
  return !sent.has(comment.id);
}

/** When the agent last answered in a thread; 0 for a thread it never answered. */
function lastAnsweredAt(comment: Comment): number {
  return comment.turns.findLast((turn) => turn.author === "author")?.at ?? 0;
}

/**
 * Which question asking in a thread puts: the reader's reply when theirs is
 * the last word, and otherwise the thread itself, by its opening comment.
 * Decided here alone: the server finds what the id names, and asks nothing
 * else of it.
 */
function questionIdOf(comment: Comment): string {
  const last = comment.turns.at(-1);
  return last?.author === "reader" ? last.id : comment.id;
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
  /** Every thread as the other side is told about it. */
  get onTheWire() {
    return comments.map(threadOnTheWire);
  },

  /** Threads that have been discussed, newest answer first. */
  get answered(): Comment[] {
    return comments
      .filter((comment) => comment.turns.length > 0)
      .sort((first, second) => lastAnsweredAt(second) - lastAnsweredAt(first));
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
    commentIds.continueFrom(draft.issued.comments);
    turnIds.continueFrom(draft.issued.turns);
    // A round the server has forgotten is still written all over the draft:
    // every thread knows the round it was written in, and every sent thread
    // the round it went out in. A restarted server comes back at round one
    // and would number the next round wrongly for everyone.
    const written = comments.reduce(
      (highest, c) => Math.max(highest, c.round),
      1,
    );
    const posted = [...sent.values()].reduce(
      (highest, round) => Math.max(highest, round + 1),
      1,
    );
    reviewStore.setRound(Math.max(reviewStore.round, written, posted));
    return comments.length;
  },

  add({ anchor, body, severity, images }: NewComment): string {
    const comment: Comment = {
      id: commentIds.next(),
      anchor,
      severity,
      body,
      images,
      turns: [],
      raised_by: "reader",
      resolved: false,
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
    anchor: Anchor,
    body: string,
    severity: CommentSeverity,
  ): string {
    const comment: Comment = {
      id,
      anchor,
      severity,
      body,
      images: [],
      turns: [],
      raised_by: "author",
      resolved: false,
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

  update(
    id: string,
    body: string,
    severity: CommentSeverity,
    images: string[],
  ) {
    sent.delete(id);
    replace(id, (c) => ({ ...c, body, severity, images }));
  },

  remove(id: string) {
    sent.delete(id);
    comments = comments.filter((c) => c.id !== id);
    remember();
  },

  /** Add what someone said to a thread. */
  addTurn(id: string, { author, body, images }: NewTurn) {
    const turn: Turn = {
      id: turnIds.next(),
      author,
      body,
      round: reviewStore.round,
      at: Date.now(),
      images,
    };
    sent.delete(id);
    replace(id, (c) => ({ ...c, turns: [...c.turns, turn] }));
  },

  /**
   * Hand a thread over to whoever is answering, and carry on reading.
   *
   * The whole thread goes, as it stands, and the server reads the question
   * out of it: the reply just written, or the comment that opened it. It
   * goes with an id, so an answer to the second question does not arrive as
   * an answer to the third — and with everything said, so it does not have
   * to guess what the thread was about.
   */
  async ask(id: string) {
    const comment = comments.find((c) => c.id === id);
    if (!comment) return;

    const questionId = questionIdOf(comment);
    replace(id, (asked) => ({
      ...asked,
      awaiting: [...asked.awaiting, { id: questionId, at: Date.now() }],
    }));

    const request: AskRequest = {
      question_id: questionId,
      thread: threadOnTheWire(comment),
    };
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
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
      id: turnIds.next(),
      author: "author",
      body: text,
      round: reviewStore.round,
      at: Date.now(),
      answers,
      images: [],
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
   * Called after a round is answered and the diff retaken. The server holds
   * that diff, so it says where each thread now hangs: one whose lines
   * survived follows them, and one whose lines are gone is marked rather than
   * left pointing at a line that has become something else.
   *
   * Says how many did each, because that is what the reader stands to lose
   * and the only part of a retake they cannot see at a glance.
   */
  async follow(): Promise<FollowOutcome> {
    const asked = comments.map((comment) => comment.id);
    const request: FollowRequest = {
      anchors: comments.map((comment) => comment.anchor),
    };
    const response = await fetch("/api/anchors/follow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Could not move the threads: ${response.status}`);
    }
    const { anchors }: FollowResponse = await response.json();
    const movedTo: Record<string, Anchor> = Object.fromEntries(
      asked.map((id, index) => [id, anchors[index]]),
    );

    let followed = 0;
    let outdated = 0;
    comments = comments.map((comment) => {
      const moved = movedTo[comment.id];
      // Written while the answer was on its way, so already on the new diff
      if (!moved) return comment;
      if (moved.outdated && !comment.anchor.outdated) outdated += 1;
      else if (anchorPlace(moved) !== anchorPlace(comment.anchor))
        followed += 1;
      return { ...comment, anchor: moved };
    });

    remember();
    return { followed, outdated };
  },

  getForFile(file: string): Comment[] {
    return comments.filter((c) => c.anchor.file === file);
  },

  clear() {
    comments = [];
    reviewBody = "";
    submitted = false;
    commentIds.reset();
    turnIds.reset();
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

    const request: SubmitRequest = {
      threads: unsent.map(threadOnTheWire),
      ...(trimmedBody ? { body: trimmedBody } : {}),
      end,
    };
    const response = await fetch("/api/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
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
    reviewStore.setRound(result.round + 1);
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
