import { SvelteSet } from "svelte/reactivity";

import { expansionStore } from "$lib/stores/expansions.svelte";
import { reviewStore } from "$lib/stores/review.svelte";
import { readChoice, readFlag, writeChoice } from "$lib/utils/preferences";

import type {
  AgentStatus,
  ContentViewMode,
  DiffFile,
  DiffLayout,
  DiffResponse,
  ReviewMode,
} from "$lib/types";

let files = $state<DiffFile[]>([]);
let selectedPath = $state<string | null>(null);
let mode = $state<ReviewMode>("diff");
let contentViewMode = $state<ContentViewMode>(
  readChoice<ContentViewMode>(
    "content-view",
    ["raw", "preview", "side-by-side"],
    "raw",
  ),
);
let title = $state("");
// What the agent last reported about itself. A push is gone once sent, so a
// review opened mid-conversation has to read it back with the diff.
let agent = $state<AgentStatus>({ model: null, context: null, at: null });
let diffLayout = $state<DiffLayout>(
  readChoice<DiffLayout>("layout", ["unified", "split"], "unified"),
);
let ignoreWhitespace = $state(readFlag("ignore-whitespace"));
// How many files have changed since this diff was taken. Zero means there
// is nothing to say: either nothing has moved, or the reader has dismissed
// it until something does.
let movedFiles = $state(0);
// What the last retake did to the threads hanging on the diff, until the
// reader looks away from it
let retaken = $state<{ followed: number; outdated: number } | null>(null);
// Paths the reader has marked done, and paths whose body is folded away.
// Marking a file viewed folds it, which is why the two are separate sets:
// a folded file can still be unread, and a viewed one can be reopened.
const viewed = new SvelteSet<string>();
const collapsed = new SvelteSet<string>();
const selectedFile = $derived(files.find((f) => f.path === selectedPath));

export const diffStore = {
  get files() {
    return files;
  },
  get selectedPath() {
    return selectedPath;
  },
  get selectedFile(): DiffFile | undefined {
    return selectedFile;
  },
  get mode(): ReviewMode {
    return mode;
  },
  get contentViewMode(): ContentViewMode {
    return contentViewMode;
  },
  /** What is under review — which repository, and against what. */
  get agent(): AgentStatus {
    return agent;
  },

  /** How many files have moved on since this diff was taken. */
  get movedFiles(): number {
    return movedFiles;
  },

  /** What the last retake did to the threads, if it is still worth saying. */
  get retaken(): { followed: number; outdated: number } | null {
    return retaken;
  },

  noteTreeMoved(files: number) {
    movedFiles = files;
  },

  /** Dismissed until the tree moves again, so a long edit does not nag. */
  dismissMoved() {
    movedFiles = 0;
  },

  noteRetaken(result: { followed: number; outdated: number }) {
    retaken = result;
    movedFiles = 0;
  },

  dismissRetaken() {
    retaken = null;
  },

  /**
   * Take the diff again, at the reader's word.
   *
   * The same act the agent performs with `claude-review round`, and it goes
   * the same way: the server retakes it and every open review is told to
   * fetch, so a browser keeps its own view of what is folded.
   */
  async retake(): Promise<void> {
    const response = await fetch("/api/round", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!response.ok) {
      throw new Error(`Could not take the diff again: ${response.status}`);
    }
  },

  get title(): string {
    return title;
  },
  /** Whether a diff reads down one column or across two. */
  get diffLayout(): DiffLayout {
    return diffLayout;
  },

  setDiffLayout(next: DiffLayout) {
    diffLayout = next;
    writeChoice("layout", next);
  },

  /** Whether whitespace-only changes are left out of the diff. */
  get ignoreWhitespace(): boolean {
    return ignoreWhitespace;
  },

  /**
   * Retake the diff with whitespace counted or not.
   *
   * Only git can answer this: which hunks vanish once whitespace stops
   * counting is not something the browser can work out from what it has.
   */
  async setIgnoreWhitespace(next: boolean) {
    ignoreWhitespace = next;
    writeChoice("ignore-whitespace", next);
    // Hunks are renumbered and re-indexed by the retake, so lines revealed
    // against the old ones would be shown under the wrong numbers
    expansionStore.clear();
    await this.fetchDiff();
  },
  get viewedCount(): number {
    return viewed.size;
  },

  isViewed(path: string): boolean {
    return viewed.has(path);
  },

  isCollapsed(path: string): boolean {
    return collapsed.has(path);
  },

  setViewed(path: string, next: boolean) {
    setMembership(viewed, path, next);
    // Finishing with a file folds it away; reopening it brings the body back
    setMembership(collapsed, path, next);
  },

  toggleViewed(path: string) {
    this.setViewed(path, !viewed.has(path));
  },

  toggleCollapsed(path: string) {
    setMembership(collapsed, path, !collapsed.has(path));
  },

  setFiles(newFiles: DiffFile[], newMode: ReviewMode, newTitle = "") {
    files = newFiles;
    mode = newMode;
    title = newTitle;
    selectedPath = newFiles.length > 0 ? newFiles[0].path : null;
  },

  /** Record which file the reader has scrolled to. */
  markInView(path: string) {
    selectedPath = path;
  },

  setContentViewMode(newMode: ContentViewMode) {
    contentViewMode = newMode;
    writeChoice("content-view", newMode);
  },

  clear() {
    files = [];
    selectedPath = null;
    mode = "diff";
    // The reader's choices about how a review is drawn outlive one review;
    // only what is on screen is cleared here
    contentViewMode = readChoice<ContentViewMode>(
      "content-view",
      ["raw", "preview", "side-by-side"],
      "raw",
    );
    diffLayout = readChoice<DiffLayout>(
      "layout",
      ["unified", "split"],
      "unified",
    );
    ignoreWhitespace = readFlag("ignore-whitespace");
    title = "";
    agent = { model: null, context: null, at: null };
    movedFiles = 0;
    retaken = null;
    viewed.clear();
    collapsed.clear();
  },

  async fetchDiff() {
    const query = ignoreWhitespace ? "?ignore_whitespace=true" : "";
    const response = await fetch(`/api/diff${query}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch diff: ${response.status}`);
    }
    const data: DiffResponse = await response.json();
    this.setFiles(data.files, data.mode, data.title);
    agent = data.agent ?? { model: null, context: null, at: null };
    // A review reloaded in the middle of a round has to learn where it is
    reviewStore.setRound(data.round ?? 1);
    if (data.answerer_attached) reviewStore.attachAnswerer();
  },
};

function setMembership(
  set: SvelteSet<string>,
  path: string,
  member: boolean,
): void {
  if (member) set.add(path);
  else set.delete(path);
}
