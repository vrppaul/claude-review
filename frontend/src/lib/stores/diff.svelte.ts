import { SvelteSet } from "svelte/reactivity";

import { expansionStore } from "$lib/stores/expansions.svelte";
import { reviewStore } from "$lib/stores/review.svelte";
import {
  readChoice,
  readFlag,
  readNumber,
  writeChoice,
} from "$lib/utils/preferences";

import type {
  AgentStatus,
  ContentViewMode,
  DiffFile,
  DiffLayout,
  DiffResponse,
  ReviewMode,
  ReviewVersion,
} from "$lib/types";

/** The review's own base: what it was opened against, and the diff it keeps. */
const REVIEW = "review";

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
// What is under review, apart from what it is compared against. The header
// says the second half itself, because that half is a control now.
let subject = $state<string | null>(null);
// Which base the diff on screen was taken against, and everything it could
// be taken against instead
let base = $state(REVIEW);
let versions = $state<ReviewVersion[]>([]);
// What the header says the diff on screen is. It comes with the diff rather
// than out of the version list, so the header can speak before it knows
// everything the diff could be compared against.
let phrase = $state("");
// What the agent last reported about itself. A push is gone once sent, so a
// review opened mid-conversation has to read it back with the diff.
let agent = $state<AgentStatus>({ model: null, context: null, at: null });
let diffLayout = $state<DiffLayout>(
  readChoice<DiffLayout>("layout", ["unified", "split"], "unified"),
);
let ignoreWhitespace = $state(readFlag("ignore-whitespace"));
// What the file tree may take. Narrower than the floor and a path is
// unreadable; wider than the ceiling and it is taking the room from what it
// is a table of contents for.
let sidebarWidth = $state(
  readNumber("sidebar-width", { min: 160, max: 560, fallback: 240 }),
);
let sidebarOpen = $state(readFlag("sidebar-open", true));
// How many files have changed since this diff was taken. Zero means there
// is nothing to say: either nothing has moved, or the reader has dismissed
// it until something does.
let movedFiles = $state(0);
// What the reader has already waved away. The tree does not move back, so
// the same number arriving again — on a reload, or with the next diff — is
// the same news they have already dismissed.
let dismissedMoved = $state(0);
// What the last retake did to the threads hanging on the diff, until the
// reader looks away from it
let retaken = $state<{ followed: number; outdated: number } | null>(null);
// Which files the last retake moved, and which round they are counted from.
// This is what takes a tick off a file the agent rewrote — without it a file
// read to the end keeps its mark through the rewrite, and gets walked past.
const changedFiles = new SvelteSet<string>();
let changedSince = $state<number | null>(null);
let knownChanged = $state(false);
// Paths the reader has marked done, and paths whose body is folded away.
// Marking a file viewed folds it, which is why the two are separate sets:
// a folded file can still be unread, and a viewed one can be reopened.
const viewed = new SvelteSet<string>();
const collapsed = new SvelteSet<string>();
const selectedFile = $derived(files.find((f) => f.path === selectedPath));

/** What the diff is asked for: whose whitespace, and against what. */
function asked(against: string): string {
  const params = new URLSearchParams();
  if (ignoreWhitespace) params.set("ignore_whitespace", "true");
  if (against !== REVIEW) params.set("base", against);
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function read(query: string): Promise<DiffResponse> {
  const response = await fetch(`/api/diff${query}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch diff: ${response.status}`);
  }
  return response.json();
}

// Which fetch is the current one. Two can be in flight — a round landing
// while the reader picks a base — and the one that started last is the one
// they asked for, whatever order the answers come back in.
let asking = 0;

/** Put a diff that has arrived on screen, with everything that came with it. */
function apply(data: DiffResponse): void {
  diffStore.setFiles(data.files, data.mode, data.title);
  subject = data.subject ?? null;
  phrase = data.phrase ?? "";
  agent = data.agent ?? { model: null, context: null, at: null };
  // Said with the diff as well as pushed: a review reloaded while the tree
  // was moving heard the push and lost it, and one opened later never heard
  // it at all
  diffStore.noteTreeMoved(data.moved ?? 0);
  // A review reloaded in the middle of a round has to learn where it is
  reviewStore.setRound(data.round ?? 1);
  if (data.answerer_attached) reviewStore.attachAnswerer();
}

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

  get sidebarWidth(): number {
    return sidebarWidth;
  },

  /** Whether the file tree is on screen. Put away, it gives its room back. */
  get sidebarOpen(): boolean {
    return sidebarOpen;
  },

  setSidebarWidth(next: number) {
    sidebarWidth = Math.min(560, Math.max(160, Math.round(next)));
    writeChoice("sidebar-width", sidebarWidth);
  },

  toggleSidebar() {
    sidebarOpen = !sidebarOpen;
    writeChoice("sidebar-open", sidebarOpen);
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
    movedFiles = files === dismissedMoved ? 0 : files;
  },

  /** Dismissed until the tree moves again, so a long edit does not nag. */
  dismissMoved() {
    dismissedMoved = movedFiles;
    movedFiles = 0;
  },

  /**
   * Note what a retake did, and take the tick off what it rewrote.
   *
   * `changed` is not `[]`: an empty list says nothing moved, while nothing
   * at all says there was no way to tell — and then no tick can be trusted,
   * so they all go. A file that loses its tick is unfolded with it, or it
   * would sit there closed and read as read.
   */
  noteRetaken(
    result: { followed: number; outdated: number },
    changed: string[] | null = null,
    since: number | null = null,
  ) {
    retaken = result;
    movedFiles = 0;
    dismissedMoved = 0;
    changedSince = since;
    changedFiles.clear();
    knownChanged = changed !== null;

    if (changed === null) {
      // Nothing is known about what moved, so nothing can keep its tick — and
      // a file that loses its tick is unfolded with it, or the whole review
      // sits closed and reads as read
      viewed.clear();
      collapsed.clear();
      return;
    }
    for (const path of changed) {
      changedFiles.add(path);
      viewed.delete(path);
      collapsed.delete(path);
    }
  },

  /** Whether the last retake rewrote this file. */
  isChanged(path: string): boolean {
    return changedFiles.has(path);
  },

  /** How many files the last retake rewrote, and from which round. */
  get changedCount(): number {
    return changedFiles.size;
  },

  /**
   * Whether the last retake could say what moved at all.
   *
   * Not the same question as whether anything moved: told nothing changed, a
   * reader stops looking, and that is the wrong thing to tell them when the
   * truth is that nobody could tell.
   */
  get changedKnown(): boolean {
    return knownChanged;
  },

  get changedSince(): number | null {
    return changedSince;
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
    sidebarWidth = readNumber("sidebar-width", {
      min: 160,
      max: 560,
      fallback: 240,
    });
    sidebarOpen = readFlag("sidebar-open", true);
    title = "";
    subject = null;
    phrase = "";
    base = REVIEW;
    versions = [];
    agent = { model: null, context: null, at: null };
    movedFiles = 0;
    dismissedMoved = 0;
    retaken = null;
    changedSince = null;
    knownChanged = false;
    changedFiles.clear();
    viewed.clear();
    collapsed.clear();
  },

  /** What is under review, without what it is compared against. */
  get subject(): string | null {
    return subject;
  },

  /** Which base the diff on screen was taken against. */
  get base(): string {
    return base;
  },

  /**
   * Whether a narrower base than the review's own is in force.
   *
   * False is the state everything else is written for: the threads are
   * anchored to the review's own diff, and only that one draws them all.
   */
  get narrowed(): boolean {
    return base !== REVIEW;
  },

  /** What the header says the diff on screen is. */
  get phrase(): string {
    return phrase;
  },

  get versions(): ReviewVersion[] {
    return versions;
  },

  async fetchVersions() {
    const response = await fetch("/api/versions");
    if (!response.ok) {
      throw new Error(`Failed to fetch versions: ${response.status}`);
    }
    versions = (await response.json()).versions;
  },

  /**
   * Read the same working tree against something else.
   *
   * Nothing about the review is written down by this. The threads stay
   * anchored to its own diff; one this base cannot draw is hidden and said
   * out loud, never moved and never marked outdated. Revealed context does
   * go — it is keyed by line numbers a different base renumbers.
   *
   * The diff arrives before the base changes. The other way round, the
   * screen spends a moment saying it is showing one thing while it is still
   * drawing another — and a base that cannot be taken leaves it saying so
   * for good.
   */
  async setBase(key: string) {
    const mine = ++asking;
    const data = await read(asked(key));
    if (mine !== asking) return;
    expansionStore.clear();
    base = key;
    apply(data);
  },

  /**
   * Take the diff again after a round, and hand back the review's own files.
   *
   * A thread is anchored in the review's diff and nowhere else, so a review
   * being read against a narrower base fetches that one too: moving threads
   * onto whatever a narrower base happens to show would rewrite every anchor
   * into somebody else's numbering.
   */
  async takeAgain(): Promise<DiffFile[]> {
    await this.fetchDiff();
    if (base === REVIEW) return files;
    return (await read(ignoreWhitespace ? "?ignore_whitespace=true" : ""))
      .files;
  },

  async fetchDiff() {
    const mine = ++asking;
    const data = await read(asked(base));
    if (mine !== asking) return;
    apply(data);
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
