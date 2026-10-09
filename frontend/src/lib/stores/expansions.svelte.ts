import { SvelteMap } from "svelte/reactivity";

import { readFileWindow } from "$lib/api/review-api";
import type { DiffLine } from "$lib/types";
import { toContextLines } from "$lib/utils/expansions";

/** Revealed lines, keyed by file path and then by the gap above a hunk. */
const revealed = new SvelteMap<string, SvelteMap<number, DiffLine[]>>();

const empty = new SvelteMap<number, DiffLine[]>();

export const expansionStore = {
  /** Lines revealed for one file, keyed by the index of the hunk below them. */
  forFile(path: string): SvelteMap<number, DiffLine[]> {
    return revealed.get(path) ?? empty;
  },

  revealedCount(path: string, hunkIndex: number): number {
    return revealed.get(path)?.get(hunkIndex)?.length ?? 0;
  },

  /**
   * Fetch a window of the file and keep it above the given hunk.
   *
   * Newly fetched lines go before the ones already there, since a gap is
   * always widened upward from the hunk below it.
   */
  async reveal(
    path: string,
    hunkIndex: number,
    start: number,
    end: number,
    oldOffset: number,
  ) {
    const window = await readFileWindow(path, start, end);
    const forPath = revealed.get(path) ?? new SvelteMap<number, DiffLine[]>();
    const existing = forPath.get(hunkIndex) ?? [];
    forPath.set(hunkIndex, [
      ...toContextLines(window.start, window.lines, oldOffset),
      ...existing,
    ]);
    revealed.set(path, forPath);
  },

  clear() {
    revealed.clear();
  },
};
