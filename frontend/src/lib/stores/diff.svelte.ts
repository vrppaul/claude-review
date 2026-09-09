import { SvelteSet } from "svelte/reactivity";

import type {
  ContentViewMode,
  DiffFile,
  DiffLayout,
  DiffResponse,
  ReviewMode,
} from "$lib/types";

let files = $state<DiffFile[]>([]);
let selectedPath = $state<string | null>(null);
let mode = $state<ReviewMode>("diff");
let contentViewMode = $state<ContentViewMode>("raw");
let title = $state("");
let diffLayout = $state<DiffLayout>("unified");
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
  get title(): string {
    return title;
  },
  /** Whether a diff reads down one column or across two. */
  get diffLayout(): DiffLayout {
    return diffLayout;
  },

  setDiffLayout(next: DiffLayout) {
    diffLayout = next;
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
    viewed.clear();
    collapsed.clear();
  },

  /** Record which file the reader has scrolled to. */
  markInView(path: string) {
    selectedPath = path;
  },

  setContentViewMode(newMode: ContentViewMode) {
    contentViewMode = newMode;
  },

  clear() {
    files = [];
    selectedPath = null;
    mode = "diff";
    contentViewMode = "raw";
    diffLayout = "unified";
    title = "";
    viewed.clear();
    collapsed.clear();
  },

  async fetchDiff() {
    const response = await fetch("/api/diff");
    if (!response.ok) {
      throw new Error(`Failed to fetch diff: ${response.status}`);
    }
    const data: DiffResponse = await response.json();
    this.setFiles(data.files, data.mode, data.title);
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
