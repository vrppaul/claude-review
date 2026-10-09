/**
 * The diff on screen: which files, taken against which base, and what else
 * it could be taken against.
 *
 * The threads are anchored to the review's own diff. A narrower base — a
 * round, a branch — is another way of reading the same working tree, and
 * nothing about the review is written down by choosing one.
 */

import { offeredVersions, retakeDiff, takeDiff } from "$lib/api/review-api";
import { RevealedContext } from "$lib/review/revealed-context.svelte";
import { TreeMoved } from "$lib/review/tree-moved.svelte";
import type { DiffFile, DiffResponse, ReviewVersion } from "$lib/types";

export class ReviewDiff {
  /** Lines revealed above the hunks of this diff. */
  readonly revealed = new RevealedContext();
  /** Files changed on disk since this diff was taken. */
  readonly treeMoved = new TreeMoved();

  readonly #whitespaceIgnored: () => boolean;
  #files = $state<DiffFile[]>([]);
  // Which base the diff on screen was taken against, by the key the server
  // named it with. Null in a review compared against nothing.
  #base = $state<string | null>(null);
  // The key of the review's own base: the diff the threads are anchored to.
  // Null in a review compared against nothing.
  #reviewKey = $state<string | null>(null);
  // Which base the reader last asked for, null for whatever the review shows
  // first. Set the moment they ask, so a diff taken again while theirs is on
  // its way — a round landing — is taken against what they picked, not
  // against what is still on screen.
  #requestedBase: string | null = null;
  #versions = $state<ReviewVersion[]>([]);
  // What the header says the diff on screen is. It comes with the diff rather
  // than out of the version list, so the header can speak before it knows
  // everything the diff could be compared against.
  #phrase = $state("");
  // The file the reader has scrolled to
  #fileInView = $state<string | null>(null);
  // Which request is the latest. Two can be in flight — a round landing
  // while the reader picks a base — and only the latest is drawn, whatever
  // order the answers come back in.
  #asking = 0;

  /**
   * @param first the diff the review opened on, against its own base
   * @param whitespaceIgnored whether the reader has whitespace-only changes left out
   */
  constructor(first: DiffResponse, whitespaceIgnored: () => boolean) {
    this.#whitespaceIgnored = whitespaceIgnored;
    this.#show(first, first.base_key);
  }

  get files(): DiffFile[] {
    return this.#files;
  }

  /** Which base the diff on screen was taken against. */
  get base(): string | null {
    return this.#base;
  }

  /** What the header says the diff on screen is. */
  get phrase(): string {
    return this.#phrase;
  }

  /** Everything the diff could be taken against, once asked for. */
  get versions(): ReviewVersion[] {
    return this.#versions;
  }

  /**
   * Whether a narrower base than the review's own is in force.
   *
   * False is the state everything else is written for: the threads are
   * anchored to the review's own diff, and only that one draws them all.
   */
  get narrowed(): boolean {
    return this.#base !== this.#reviewKey;
  }

  /** The file the reader has scrolled to. */
  get fileInView(): string | null {
    return this.#fileInView;
  }

  /** Record which file the reader has scrolled to. */
  markInView(path: string): void {
    this.#fileInView = path;
  }

  /** Take the diff again against the base the reader asked for. */
  async take(): Promise<void> {
    const mine = ++this.#asking;
    const against = this.#requestedBase;
    const data = await takeDiff({
      ignoreWhitespace: this.#whitespaceIgnored(),
      base: against,
    });
    if (mine !== this.#asking) return;
    this.#show(data, against ?? data.base_key);
  }

  /**
   * Read the same working tree against something else.
   *
   * The threads stay anchored to the review's own diff; one this base
   * cannot draw is hidden and said out loud, never moved and never marked
   * outdated.
   *
   * The diff arrives before the base changes. The other way round, the
   * screen spends a moment saying it is showing one thing while it is still
   * drawing another — and a base that cannot be taken leaves it saying so
   * for good.
   */
  async setBase(key: string): Promise<void> {
    this.#requestedBase = key;
    try {
      await this.take();
    } catch (error) {
      // A base that cannot be taken is not asked for again by the next retake
      if (this.#requestedBase === key) this.#requestedBase = this.#base;
      throw error;
    }
  }

  /** Put the review's own diff back, with every thread it holds. */
  async showWholeReview(): Promise<void> {
    if (this.#reviewKey === null) return;
    await this.setBase(this.#reviewKey);
  }

  /** Ask what the diff could be taken against. */
  async loadVersions(): Promise<void> {
    this.#versions = (await offeredVersions()).versions;
  }

  /**
   * Take the diff again, at the reader's word.
   *
   * The same act the agent performs with `claude-review retake`, and it goes
   * the same way: the server retakes it and every open review is told to
   * fetch, so a browser keeps its own view of what is folded.
   */
  async retake(): Promise<void> {
    await retakeDiff();
  }

  /** Put a diff that has arrived on screen, with everything that came with it. */
  #show(data: DiffResponse, base: string | null): void {
    this.revealed.forget();
    this.#files = data.files;
    this.#fileInView = data.files[0]?.path ?? null;
    this.#base = base;
    this.#reviewKey = data.review_key;
    // None when the review is compared against nothing: files, a transcript
    this.#phrase = data.phrase ?? "";
    // Said with the diff as well as pushed: a review reloaded while the tree
    // was moving heard the push and lost it, and one opened later never
    // heard it at all
    this.treeMoved.note(data.moved);
  }
}
