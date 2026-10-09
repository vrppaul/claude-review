/**
 * One review, opened: what it is, the diff on screen, the threads written
 * on it, the conversation beside it, and the reader's way of reading it.
 *
 * Built only once the review is known and its first diff has arrived, so
 * nothing in it has a "not loaded yet" to be asked about. Each part owns its
 * own state; what spans parts — whitespace retaking the diff, a retake
 * narrowing to what changed — is done here.
 */

import { Guide } from "$lib/guide/guide.svelte";
import type { PageConnection } from "$lib/connection/page-connection";
import type { PageLayout } from "$lib/reader/page-layout.svelte";
import type { ReplySound } from "$lib/reader/reply-sound";
import type { Settings } from "$lib/reader/settings.svelte";
import { Answerer } from "$lib/review/answerer.svelte";
import { CommentFields } from "$lib/review/comment-fields";
import { Conversation } from "$lib/review/conversation.svelte";
import { FileSections } from "$lib/review/file-sections";
import { LastRetake } from "$lib/review/last-retake.svelte";
import { ReadingProgress } from "$lib/review/reading-progress.svelte";
import { ReviewDiff } from "$lib/review/review-diff.svelte";
import { Rounds } from "$lib/review/rounds.svelte";
import { Submission } from "$lib/review/submission.svelte";
import { ThreadNavigator } from "$lib/review/thread-navigator";
import { Threads } from "$lib/review/threads.svelte";
import type {
  ChangesSince,
  DiffResponse,
  FollowOutcome,
  ReviewMode,
  ReviewResponse,
  SendLimits,
  SessionHello,
} from "$lib/types";
import type { Draft } from "$lib/utils/drafts";
import { reviewWeight } from "$lib/utils/weight";

/** What a review opens on: what the server says it is, its first diff, and any unsent draft. */
export interface Opening {
  facts: ReviewResponse;
  firstDiff: DiffResponse;
  draft: Draft | null;
}

/** What belongs to the reader rather than to the review, and outlives it. */
export interface ReaderParts {
  settings: Settings;
  layout: PageLayout;
  sound: ReplySound;
}

export class Review {
  /** What is under review — which repository, and against what. */
  readonly title: string;
  readonly mode: ReviewMode;
  /** What the server takes: pasted images, and the lines one comment covers. */
  readonly limits: SendLimits;

  readonly settings: Settings;
  readonly layout: PageLayout;
  readonly sound: ReplySound;

  readonly rounds: Rounds;
  readonly answerer: Answerer;
  readonly diff: ReviewDiff;
  readonly reading = new ReadingProgress();
  readonly lastRetake = new LastRetake();
  readonly threads: Threads;
  readonly submission: Submission;
  readonly conversation: Conversation;
  readonly guide: Guide;
  readonly sections = new FileSections();
  readonly navigator: ThreadNavigator;
  readonly commentFields = new CommentFields();

  // How many threads came back from the draft, so the reader is told rather
  // than left to wonder where they came from; zero once they have seen it
  #restoredCount: number;
  // What handing this review over costs, as far as this side can tell
  readonly #weight: number;
  // What the page tells the server it holds: the round it has reached, and
  // the threads, which are unsent work and live only here
  readonly #hello: SessionHello;

  constructor({ facts, firstDiff, draft }: Opening, reader: ReaderParts) {
    this.title = facts.title;
    this.mode = facts.mode;
    this.limits = facts.limits;
    this.settings = reader.settings;
    this.layout = reader.layout;
    this.sound = reader.sound;

    this.rounds = new Rounds(facts.round);
    this.answerer = new Answerer(facts.answerer_attached, facts.agent);
    this.diff = new ReviewDiff(
      firstDiff,
      () => this.settings.current.ignore_whitespace,
    );
    this.threads = new Threads(this.rounds, facts.title, draft);
    this.submission = new Submission(
      this.threads,
      this.rounds,
      facts.title,
      draft,
    );
    this.conversation = new Conversation(facts.title, draft);
    this.guide = new Guide(this.answerer, facts.release);
    this.navigator = new ThreadNavigator(this.reading, this.sections);
    this.#restoredCount = $state(draft === null ? 0 : this.threads.count);
    this.#weight = $derived(reviewWeight(this.diff.files, this.threads.all));
    this.#hello = $derived({
      round: this.rounds.current,
      threads: this.threads.onTheWire,
    });
  }

  get restoredCount(): number {
    return this.#restoredCount;
  }

  dismissRestored(): void {
    this.#restoredCount = 0;
  }

  /** What handing this review over costs, in tokens, as far as this side can tell. */
  get weight(): number {
    return this.#weight;
  }

  /** The most lines one comment may cover. */
  get longestQuotedRange(): number {
    return this.limits.max_quoted_lines;
  }

  /**
   * Keep the server told what this page holds, for as long as it is open:
   * an agent that attaches later has no other way to learn the threads
   * exist, and a restarted server knows only round one. Returns how to stop.
   */
  tellServerThrough(connection: Pick<PageConnection, "greet">): () => void {
    return $effect.root(() => {
      $effect(() => connection.greet(this.#hello));
    });
  }

  /**
   * Retake the diff with whitespace counted or not.
   *
   * Only git can answer this: which hunks vanish once whitespace stops
   * counting is not something the browser can work out from what it has.
   */
  async setIgnoreWhitespace(next: boolean): Promise<void> {
    await this.settings.change({ ignore_whitespace: next });
    await this.diff.take();
  }

  /**
   * Note what a retake did, and take the tick off what it rewrote. Whatever
   * moved on disk is in the diff now, so the tree has nothing left to say.
   */
  noteRetake(outcome: FollowOutcome, changes: ChangesSince | null): void {
    this.diff.treeMoved.settle();
    this.lastRetake.note(outcome, changes);
    this.reading.forgetRewritten(changes);
  }

  /** Read only what changed since the round the last retake was counted from. */
  async showChangesSinceRetake(): Promise<void> {
    const since = this.lastRetake.changedSinceKey;
    if (since === null) return;
    await this.diff.setBase(since);
  }
}
