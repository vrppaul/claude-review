import { SvelteMap } from "svelte/reactivity";

import type { DiffLine } from "$lib/types";
import { toContextLines } from "$lib/utils/expansions";

interface FileWindow {
  start: number;
  lines: string[];
  total: number;
}

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
    oldOffset = 0,
  ) {
    const params = new URLSearchParams({
      path,
      start: String(start),
      end: String(end),
    });
    const response = await fetch(`/api/file-window?${params}`);
    if (!response.ok) {
      throw new Error(`Could not read ${path}: ${response.status}`);
    }

    const window: FileWindow = await response.json();
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
