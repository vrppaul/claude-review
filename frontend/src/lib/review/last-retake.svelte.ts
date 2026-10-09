/**
 * What the last retake of the diff did, until the reader looks away from it:
 * how the threads fared, and which files it rewrote since which round.
 */

import { SvelteSet } from "svelte/reactivity";

import type { ChangesSince, FollowOutcome } from "$lib/types";

export class LastRetake {
  // How the threads fared, while it is still worth saying
  #outcome = $state<FollowOutcome | null>(null);
  // Which files the retake rewrote. This is what takes a tick off a file
  // the agent rewrote — without it a file read to the end keeps its mark
  // through the rewrite, and gets walked past.
  readonly #changed = new SvelteSet<string>();
  #sinceRound = $state<number | null>(null);
  // The key that shows only what changed since that round, as the server
  // named it
  #sinceKey: string | null = null;
  #known = $state(false);

  /** What the retake did to the threads, if it is still worth saying. */
  get outcome(): FollowOutcome | null {
    return this.#outcome;
  }

  /** Whether the retake rewrote this file. */
  isChanged(path: string): boolean {
    return this.#changed.has(path);
  }

  /** How many files the retake rewrote. */
  get changedCount(): number {
    return this.#changed.size;
  }

  /** Which round the rewritten files are counted from. */
  get changedSince(): number | null {
    return this.#sinceRound;
  }

  /** The base that shows only what changed since that round. */
  get changedSinceKey(): string | null {
    return this.#sinceKey;
  }

  /**
   * Whether the retake could say what moved at all.
   *
   * Not the same question as whether anything moved: told nothing changed,
   * a reader stops looking, and that is the wrong thing to tell them when
   * the truth is that nobody could tell.
   */
  get changedKnown(): boolean {
    return this.#known;
  }

  /** Note what a retake did; no `changes` says there was no way to tell. */
  note(outcome: FollowOutcome, changes: ChangesSince | null): void {
    this.#outcome = outcome;
    this.#sinceRound = changes?.since_round ?? null;
    this.#sinceKey = changes?.base_key ?? null;
    this.#known = changes !== null;
    this.#changed.clear();
    for (const path of changes?.paths ?? []) this.#changed.add(path);
  }

  /** The reader has seen what the threads did. */
  dismiss(): void {
    this.#outcome = null;
  }
}
