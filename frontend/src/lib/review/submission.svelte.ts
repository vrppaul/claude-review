/**
 * Sending the review: the summary written for it, the rounds sent while it
 * stays open, and the end.
 */

import { endReview, submitReview } from "$lib/api/review-api";
import type { Rounds } from "$lib/review/rounds.svelte";
import type { Threads } from "$lib/review/threads.svelte";
import type { SubmitResponse } from "$lib/types";
import { clearDraft, type Draft, saveDraft } from "$lib/utils/drafts";
import { threadOnTheWire } from "$lib/utils/thread-wire";

export class Submission {
  readonly #threads: Threads;
  readonly #rounds: Rounds;
  readonly #title: string;
  // The summary: about the change as a whole, not one line of it
  #body: string;
  #finished = $state(false);

  /**
   * @param title what the review is of, which its draft is kept under
   * @param draft an unsent review of the same thing, with its summary
   */
  constructor(
    threads: Threads,
    rounds: Rounds,
    title: string,
    draft: Draft | null,
  ) {
    this.#threads = threads;
    this.#rounds = rounds;
    this.#title = title;
    this.#body = $state(draft?.reviewBody ?? "");
  }

  get body(): string {
    return this.#body;
  }

  /** Whether the review is over — sent for good, or ended — and the page is done. */
  get finished(): boolean {
    return this.#finished;
  }

  /** Whether there is anything to send at all. */
  get hasContent(): boolean {
    return this.#threads.count > 0 || this.#body.trim().length > 0;
  }

  /** Whether there is anything the answering side has not been told yet. */
  get hasUnsent(): boolean {
    return this.#threads.unsent.length > 0 || this.#body.trim().length > 0;
  }

  setBody(text: string): void {
    this.#body = text;
    saveDraft({ title: this.#title, reviewBody: text });
  }

  /**
   * Send what has been written since the last time.
   *
   * `end` decides whether this is the last word: a round leaves the review
   * open, so the answers to it have somewhere to come back to.
   */
  async submit(end: boolean): Promise<SubmitResponse> {
    const summary = this.#body.trim();
    const unsent = this.#threads.unsent;

    const result = await submitReview({
      threads: unsent.map(threadOnTheWire),
      ...(summary ? { body: summary } : {}),
      end,
    });

    if (end) {
      this.#finish();
      return result;
    }

    // A round is a line under what was said, not the end of it: the threads
    // stay, and only what happens next is new
    this.#threads.markSent(unsent, result.round);
    this.setBody("");
    this.#rounds.reach(result.round + 1);
    return result;
  }

  /** End a review that was being worked through in rounds. */
  async end(): Promise<void> {
    await endReview();
    this.#finish();
  }

  #finish(): void {
    this.#finished = true;
    // The review has left; keeping it would greet the next one as unsent work
    clearDraft();
  }
}
