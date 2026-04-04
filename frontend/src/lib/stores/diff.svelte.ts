import type { DiffFile, DiffResponse } from '$lib/types';

let files = $state<DiffFile[]>([]);
let selectedPath = $state<string | null>(null);

export const diffStore = {
	get files() {
		return files;
	},
	get selectedPath() {
		return selectedPath;
	},
	get selectedFile(): DiffFile | undefined {
		return files.find((f) => f.path === selectedPath);
	},

	setFiles(newFiles: DiffFile[]) {
		files = newFiles;
		selectedPath = newFiles.length > 0 ? newFiles[0].path : null;
	},

	selectFile(path: string) {
		selectedPath = path;
	},

	async fetchDiff() {
		const response = await fetch('/api/diff');
		if (!response.ok) {
			throw new Error(`Failed to fetch diff: ${response.status}`);
		}
		const data: DiffResponse = await response.json();
		this.setFiles(data.files);
	}
};
