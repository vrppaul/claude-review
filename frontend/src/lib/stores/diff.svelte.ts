import type {
  ContentViewMode,
  DiffFile,
  DiffResponse,
  ReviewMode,
} from "$lib/types";

let files = $state<DiffFile[]>([]);
let selectedPath = $state<string | null>(null);
let mode = $state<ReviewMode>("diff");
let contentViewMode = $state<ContentViewMode>("raw");
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

  setFiles(newFiles: DiffFile[], newMode: ReviewMode) {
    files = newFiles;
    mode = newMode;
    selectedPath = newFiles.length > 0 ? newFiles[0].path : null;
  },

  selectFile(path: string) {
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
  },

  async fetchDiff() {
    const response = await fetch("/api/diff");
    if (!response.ok) {
      throw new Error(`Failed to fetch diff: ${response.status}`);
    }
    const data: DiffResponse = await response.json();
    this.setFiles(data.files, data.mode);
  },
};
