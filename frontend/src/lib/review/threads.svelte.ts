/**
 * The threads of the review: what the reader wrote, what the agent raised,
 * and everything said in each since.
 *
 * They are unsent work and live only in this page until a round carries
 * them, so the draft keeps them across a reload, and the server is told
 * what the page holds for an agent that attaches later.
 */

import { SvelteMap } from "svelte/reactivity";

import { askInThread, followAnchors } from "$lib/api/review-api";
import { anchorPlace } from "$lib/anchors/views";
import type { Rounds } from "$lib/review/rounds.svelte";
import type {
  Anchor,
  Comment,
  CommentSeverity,
  FollowOutcome,
  NewComment,
  NewTurn,
  ThreadInput,
  Turn,
} from "$lib/types";
import { type Draft, saveDraft } from "$lib/utils/drafts";
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from "$lib/utils/ids";
import { threadOnTheWire } from "$lib/utils/thread-wire";

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

/** What a file with no threads holds. */
const NO_THREADS: readonly Comment[] = [];

export class Threads {
  readonly #rounds: Rounds;
  // What the draft is tied to, so it is not restored onto another review
  readonly #title: string;
  #all = $state<Comment[]>([]);
  // Which threads have gone out, and in which round. A round carries what
  // is new since the last one, not the whole review again — and the reader
  // can see which of what is on screen the answering side has already read.
  readonly #sent = new SvelteMap<string, number>();
  readonly #commentIds = new IdSequence(COMMENT_ID_PREFIX);
  readonly #turnIds = new IdSequence(TURN_ID_PREFIX);
  // Where the reader is in the list, shared by every control that steps it
  #cursor = -1;
  // By the file they hang on, so a file asks for its own without a scan
  readonly #byFile = $derived(
    Map.groupBy(this.#all, (comment) => comment.anchor.file),
  );
  readonly #unread = $derived(this.#all.filter((comment) => comment.unread));
  readonly #unsent = $derived(
    this.#all.filter((comment) => !this.#sent.has(comment.id)),
  );
  readonly #onTheWire = $derived(this.#all.map(threadOnTheWire));

  /**
   * @param rounds the round each thread and turn is stamped with
   * @param title what the review is of, which its draft is kept under
   * @param draft an unsent review of the same thing, picked up where it stopped
   */
  constructor(rounds: Rounds, title: string, draft: Draft | null) {
    this.#rounds = rounds;
    this.#title = title;
    if (draft !== null) this.#pickUp(draft);
  }

  get all(): Comment[] {
    return this.#all;
  }

  get count(): number {
    return this.#all.length;
  }

  /** Threads carrying an answer nobody has looked at. */
  get unread(): Comment[] {
    return this.#unread;
  }

  /** Threads the answering side has not been told about yet. */
  get unsent(): Comment[] {
    return this.#unsent;
  }

  /** Every thread as the other side is told about it. */
  get onTheWire(): ThreadInput[] {
    return this.#onTheWire;
  }

  /** Threads that have been discussed, newest answer first. */
  get answered(): Comment[] {
    return this.#all
      .filter((comment) => comment.turns.length > 0)
      .sort((first, second) => lastAnsweredAt(second) - lastAnsweredAt(first));
  }

  /** The threads hanging on one file. */
  onFile(path: string): readonly Comment[] {
    return this.#byFile.get(path) ?? NO_THREADS;
  }

  /** Which round a thread went out in, or nothing if it has not yet. */
  sentInRound(id: string): number | undefined {
    return this.#sent.get(id);
  }

  /** Step to the next or previous thread, and say which it is. */
  step(direction: 1 | -1): Comment | undefined {
    if (this.#all.length === 0) return undefined;
    this.#cursor =
      (this.#cursor + direction + this.#all.length) % this.#all.length;
    return this.#all[this.#cursor];
  }

  add({ anchor, body, severity, images }: NewComment): string {
    const comment: Comment = {
      id: this.#commentIds.next(),
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
      round: this.#rounds.current,
      at: Date.now(),
    };
    this.#all = [...this.#all, comment];
    this.#remember();
    return comment.id;
  }

  /**
   * Take a thread the agent raised and put it on the diff.
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
      round: this.#rounds.current,
      at: Date.now(),
    };
    this.#all = [...this.#all, comment];
    this.#sent.set(id, this.#rounds.current);
    this.#remember();
    return id;
  }

  update(
    id: string,
    body: string,
    severity: CommentSeverity,
    images: string[],
  ): void {
    this.#sent.delete(id);
    this.#replace(id, (comment) => ({ ...comment, body, severity, images }));
  }

  remove(id: string): void {
    this.#sent.delete(id);
    this.#all = this.#all.filter((comment) => comment.id !== id);
    this.#remember();
  }

  /** Add what someone said to a thread. */
  addTurn(id: string, { author, body, images }: NewTurn): void {
    const turn: Turn = {
      id: this.#turnIds.next(),
      author,
      body,
      round: this.#rounds.current,
      at: Date.now(),
      images,
    };
    this.#sent.delete(id);
    this.#replace(id, (comment) => ({
      ...comment,
      turns: [...comment.turns, turn],
    }));
  }

  /**
   * Hand a thread over to whoever is answering, and carry on reading.
   *
   * The whole thread goes, as it stands, and the server reads the question
   * out of it: the reply just written, or the comment that opened it. It
   * goes with an id, so an answer to the second question does not arrive as
   * an answer to the third — and with everything said, so it does not have
   * to guess what the thread was about.
   */
  async ask(id: string): Promise<void> {
    const comment = this.#all.find((candidate) => candidate.id === id);
    if (!comment) return;

    const questionId = questionIdOf(comment);
    this.#replace(id, (asked) => ({
      ...asked,
      awaiting: [...asked.awaiting, { id: questionId, at: Date.now() }],
    }));

    try {
      await askInThread({
        question_id: questionId,
        thread: threadOnTheWire(comment),
      });
    } catch (error) {
      this.#replace(id, (asked) => ({
        ...asked,
        awaiting: asked.awaiting.filter((waiting) => waiting.id !== questionId),
      }));
      throw error;
    }
  }

  /**
   * Take an answer that came back and put it under the question it answers.
   *
   * An answerer that names the question is believed; one that does not gets
   * the oldest question still waiting, which is the order they were handed
   * over in.
   */
  receiveReply(id: string, text: string, questionId: string | null): void {
    const comment = this.#all.find((candidate) => candidate.id === id);
    if (!comment) return;

    const answers = questionId ?? comment.awaiting[0]?.id;
    const turn: Turn = {
      id: this.#turnIds.next(),
      author: "author",
      body: text,
      round: this.#rounds.current,
      at: Date.now(),
      answers,
      images: [],
    };
    // Not marked unsent: the answer came from the side that reads the
    // rounds, so sending it back would only repeat what they wrote
    this.#replace(id, (answered) => ({
      ...answered,
      turns: [...answered.turns, turn],
      awaiting: answered.awaiting.filter((waiting) => waiting.id !== answers),
      unread: true,
    }));
  }

  markRead(id: string): void {
    if (!this.#all.some((comment) => comment.id === id && comment.unread)) {
      return;
    }
    this.#replace(id, (comment) => ({ ...comment, unread: false }));
  }

  markAllRead(): void {
    this.#all = this.#all.map((comment) =>
      comment.unread ? { ...comment, unread: false } : comment,
    );
    this.#remember();
  }

  setResolved(id: string, resolved: boolean): void {
    this.#sent.delete(id);
    this.#replace(id, (comment) => ({ ...comment, resolved }));
  }

  /** Fold a thread away, or bring it back. Not a state the review carries. */
  setCollapsed(id: string, collapsed: boolean): void {
    this.#replace(id, (comment) => ({ ...comment, collapsed }));
  }

  /** Note that these threads went out in this round. */
  markSent(sent: Comment[], round: number): void {
    for (const comment of sent) this.#sent.set(comment.id, round);
    this.#remember();
  }

  /**
   * Move every thread onto the diff as it now stands.
   *
   * Called after a round is answered and the diff retaken. The server holds
   * that diff, so it says where each thread now hangs: one whose lines
   * survived follows them, and one whose lines are gone is marked rather
   * than left pointing at a line that has become something else.
   *
   * Says how many did each, because that is what the reader stands to lose
   * and the only part of a retake they cannot see at a glance.
   */
  async follow(): Promise<FollowOutcome> {
    const asked = this.#all.map((comment) => comment.id);
    const { anchors } = await followAnchors({
      anchors: this.#all.map((comment) => comment.anchor),
    });
    const movedTo: Record<string, Anchor> = Object.fromEntries(
      asked.map((id, index) => [id, anchors[index]]),
    );

    let followed = 0;
    let outdated = 0;
    this.#all = this.#all.map((comment) => {
      const moved = movedTo[comment.id];
      // Written while the answer was on its way, so already on the new diff
      if (!moved) return comment;
      if (moved.outdated && !comment.anchor.outdated) outdated += 1;
      else if (anchorPlace(moved) !== anchorPlace(comment.anchor))
        followed += 1;
      return { ...comment, anchor: moved };
    });

    this.#remember();
    return { followed, outdated };
  }

  /**
   * Pick up an unsent review of the same thing.
   *
   * A round the server has forgotten is still written all over the draft:
   * every thread knows the round it was written in, and every sent thread
   * the round it went out in. A restarted server comes back at round one
   * and would number the next round wrongly for everyone.
   */
  #pickUp(draft: Draft): void {
    this.#all = draft.comments;
    for (const [id, round] of draft.sent) this.#sent.set(id, round);
    this.#commentIds.continueFrom(draft.issued.comments);
    this.#turnIds.continueFrom(draft.issued.turns);
    for (const comment of this.#all) this.#rounds.reach(comment.round);
    for (const round of this.#sent.values()) this.#rounds.reach(round + 1);
  }

  #replace(id: string, change: (comment: Comment) => Comment): void {
    this.#all = this.#all.map((comment) =>
      comment.id === id ? change(comment) : comment,
    );
    this.#remember();
  }

  #remember(): void {
    saveDraft({
      title: this.#title,
      comments: this.#all,
      sent: [...this.#sent],
      issued: {
        comments: this.#commentIds.issued,
        turns: this.#turnIds.issued,
      },
    });
  }
}
