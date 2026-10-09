/**
 * How far the reader has got through the files: which are done, and which
 * are folded away.
 *
 * Marking a file viewed folds it, which is why the two are separate: a
 * folded file can still be unread, and a viewed one can be opened again.
 */

import { SvelteSet } from "svelte/reactivity";

import type { ChangesSince } from "$lib/types";

export class ReadingProgress {
  readonly #viewed = new SvelteSet<string>();
  readonly #folded = new SvelteSet<string>();

  get viewedCount(): number {
    return this.#viewed.size;
  }

  isViewed(path: string): boolean {
    return this.#viewed.has(path);
  }

  isFolded(path: string): boolean {
    return this.#folded.has(path);
  }

  /** Finishing with a file folds it away; opening it again brings the body back. */
  setViewed(path: string, viewed: boolean): void {
    setMembership(this.#viewed, path, viewed);
    setMembership(this.#folded, path, viewed);
  }

  toggleViewed(path: string): void {
    this.setViewed(path, !this.#viewed.has(path));
  }

  toggleFolded(path: string): void {
    setMembership(this.#folded, path, !this.#folded.has(path));
  }

  unfold(path: string): void {
    this.#folded.delete(path);
  }

  /**
   * Take the tick off what a retake rewrote, and bring it back into view.
   *
   * No `changes` is not no change: it says there was no way to tell — and
   * then no tick can be trusted, so they all go. A file that loses its tick
   * is unfolded with it, or it would sit there closed and read as read.
   */
  forgetRewritten(changes: ChangesSince | null): void {
    if (changes === null) {
      this.#viewed.clear();
      this.#folded.clear();
      return;
    }
    for (const path of changes.paths) {
      this.#viewed.delete(path);
      this.#folded.delete(path);
    }
  }
}

function setMembership(
  set: SvelteSet<string>,
  path: string,
  member: boolean,
): void {
  if (member) set.add(path);
  else set.delete(path);
}
