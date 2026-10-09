import { SvelteSet } from "svelte/reactivity";

import { offeredVersions, retakeDiff, takeDiff } from "$lib/api/review-api";
import { expansionStore } from "$lib/stores/expansions.svelte";
import { settingsStore } from "$lib/stores/settings.svelte";
import {
  readChoice,
  readFlag,
  readNumber,
  writeChoice,
} from "$lib/utils/preferences";

import type {
  ChangesSince,
  ContentViewMode,
  FollowOutcome,
  DiffFile,
  DiffLayout,
  DiffResponse,
  SendLimits,
  ReviewMode,
  ReviewResponse,
  ReviewVersion,
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
// Which base the diff on screen was taken against, by the key the server
// named it with, and everything it could be taken against instead. Null until
// the first diff arrives, and in a review compared against nothing.
let base = $state<string | null>(null);
// The key of the review's own base, as the server names it: the diff the
// threads are anchored to. Null in a review compared against nothing.
let reviewKey = $state<string | null>(null);
// Which base the reader last asked for, null for whatever the review shows
// first. Set the moment they ask, so a diff taken again while theirs is on
// its way — a round landing — is taken against what they picked, not against
// what is still on screen.
let requestedBase: string | null = null;
let versions = $state<ReviewVersion[]>([]);
// What the header says the diff on screen is. It comes with the diff rather
// than out of the version list, so the header can speak before it knows
// everything the diff could be compared against.
let phrase = $state("");
// What the server takes: pasted images, and the lines one comment covers.
// Null until the review has been read, and nothing can be pasted or selected
// before then: there is nothing on screen yet.
let sendLimits = $state<SendLimits | null>(null);
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
let retaken = $state<FollowOutcome | null>(null);
// Which files the last retake moved, and which round they are counted from.
// This is what takes a tick off a file the agent rewrote — without it a file
// read to the end keeps its mark through the rewrite, and gets walked past.
const changedFiles = new SvelteSet<string>();
let changedSince = $state<number | null>(null);
// The key that shows only what changed since that round, as the server named it
let changedSinceKey: string | null = null;
let knownChanged = $state(false);
// Paths the reader has marked done, and paths whose body is folded away.
// Marking a file viewed folds it, which is why the two are separate sets:
// a folded file can still be unread, and a viewed one can be reopened.
const viewed = new SvelteSet<string>();
const collapsed = new SvelteSet<string>();
const selectedFile = $derived(files.find((f) => f.path === selectedPath));

// Which request is the latest. Two can be in flight — a round landing while
// the reader picks a base — and only the latest is drawn, whatever order the
// answers come back in.
let asking = 0;

/**
 * Take the diff against the base the reader asked for, and put it on screen.
 *
 * Only the answer to the latest request is drawn, whatever order the
 * answers come back in.
 */
async function take(): Promise<void> {
  const mine = ++asking;
  const against = requestedBase;
  const data = await takeDiff({
    ignoreWhitespace: settingsStore.settings.ignore_whitespace,
    base: against,
  });
  if (mine !== asking) return;
  base = against ?? data.base_key;
  reviewKey = data.review_key;
  apply(data);
}

/** Put a diff that has arrived on screen, with everything that came with it. */
function apply(data: DiffResponse): void {
  // Revealed lines sit above hunks counted by position, and a new diff
  // counts them afresh: a round, a base, whitespace all renumber them
  expansionStore.clear();
  show(data.files);
  // None when the review is compared against nothing: files, a transcript
  phrase = data.phrase ?? "";
  // Said with the diff as well as pushed: a review reloaded while the tree
  // was moving heard the push and lost it, and one opened later never heard
  // it at all
  diffStore.noteTreeMoved(data.moved);
}

/** Draw these files, starting from the first. */
function show(newFiles: DiffFile[]): void {
  files = newFiles;
  selectedPath = newFiles.length > 0 ? newFiles[0].path : null;
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
  get limits(): SendLimits | null {
    return sendLimits;
  },
  /** The most lines one comment may cover, once the server has said. */
  get longestQuotedRange(): number | null {
    return sendLimits?.max_quoted_lines ?? null;
  },

  setLimits(limits: SendLimits) {
    sendLimits = limits;
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
  get retaken(): FollowOutcome | null {
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
   * No `changes` is not no change: it says there was no way to tell — and
   * then no tick can be trusted, so they all go. A file that loses its tick
   * is unfolded with it, or it would sit there closed and read as read.
   */
  noteRetaken(result: FollowOutcome, changes: ChangesSince | null) {
    retaken = result;
    movedFiles = 0;
    dismissedMoved = 0;
    changedSince = changes?.since_round ?? null;
    changedSinceKey = changes?.base_key ?? null;
    changedFiles.clear();
    knownChanged = changes !== null;

    if (changes === null) {
      // Nothing is known about what moved, so nothing can keep its tick — and
      // a file that loses its tick is unfolded with it, or the whole review
      // sits closed and reads as read
      viewed.clear();
      collapsed.clear();
      return;
    }
    for (const path of changes.paths) {
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
   * The same act the agent performs with `claude-review retake`, and it goes
   * the same way: the server retakes it and every open review is told to
   * fetch, so a browser keeps its own view of what is folded.
   */
  async retake(): Promise<void> {
    await retakeDiff();
  },

  get title(): string {
    return title;
  },
  /** Whether a diff reads down one column or across two. */
  get diffLayout(): DiffLayout {
    return settingsStore.settings.diff_layout;
  },

  setDiffLayout(next: DiffLayout) {
    void settingsStore.change({ diff_layout: next });
  },

  /** Whether whitespace-only changes are left out of the diff. */
  get ignoreWhitespace(): boolean {
    return settingsStore.settings.ignore_whitespace;
  },

  /**
   * Retake the diff with whitespace counted or not.
   *
   * Only git can answer this: which hunks vanish once whitespace stops
   * counting is not something the browser can work out from what it has.
   */
  async setIgnoreWhitespace(next: boolean) {
    await settingsStore.change({ ignore_whitespace: next });
    await take();
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
    show(newFiles);
    mode = newMode;
    title = newTitle;
  },

  /** Take in what the review is, as the page opens: none of it changes afterwards. */
  learn(facts: ReviewResponse) {
    mode = facts.mode;
    title = facts.title;
    sendLimits = facts.limits;
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
    sidebarWidth = readNumber("sidebar-width", {
      min: 160,
      max: 560,
      fallback: 240,
    });
    sidebarOpen = readFlag("sidebar-open", true);
    title = "";
    phrase = "";
    base = null;
    reviewKey = null;
    requestedBase = null;
    versions = [];
    sendLimits = null;
    movedFiles = 0;
    dismissedMoved = 0;
    retaken = null;
    changedSince = null;
    changedSinceKey = null;
    knownChanged = false;
    changedFiles.clear();
    viewed.clear();
    collapsed.clear();
  },

  /** Which base the diff on screen was taken against. */
  get base(): string | null {
    return base;
  },

  /**
   * Whether a narrower base than the review's own is in force.
   *
   * False is the state everything else is written for: the threads are
   * anchored to the review's own diff, and only that one draws them all.
   */
  get narrowed(): boolean {
    return base !== reviewKey;
  },

  /** What the header says the diff on screen is. */
  get phrase(): string {
    return phrase;
  },

  get versions(): ReviewVersion[] {
    return versions;
  },

  async fetchVersions() {
    versions = (await offeredVersions()).versions;
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
    requestedBase = key;
    try {
      await take();
    } catch (error) {
      // A base that cannot be taken is not asked for again by the next retake
      if (requestedBase === key) requestedBase = base;
      throw error;
    }
  },

  async fetchDiff() {
    await take();
  },

  /** Read only what changed since the round the last retake was counted from. */
  async showChangesSinceRetake() {
    if (changedSinceKey === null) return;
    await this.setBase(changedSinceKey);
  },

  /** Put the review's own diff back, with every thread it holds. */
  async showWholeReview() {
    if (reviewKey === null) return;
    await this.setBase(reviewKey);
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
