import { describe, it, expect, beforeEach, vi } from 'vitest';
import { diffStore } from '$lib/stores/diff.svelte';
import type { DiffFile } from '$lib/types';

const mockFiles: DiffFile[] = [
	{
		path: 'src/a.ts',
		status: 'modified',
		hunks: [
			{
				header: '@@ -1,3 +1,4 @@',
				old_start: 1,
				new_start: 1,
				lines: [
					{ type: 'context', old_no: 1, new_no: 1, content: 'const x = 1;' },
					{ type: 'add', old_no: null, new_no: 2, content: 'const y = 2;' }
				]
			}
		]
	},
	{
		path: 'src/b.ts',
		status: 'added',
		hunks: []
	}
];

describe('diffStore', () => {
	beforeEach(() => {
		diffStore.setFiles([]);
	});

	it('starts with empty files', () => {
		expect(diffStore.files).toEqual([]);
		expect(diffStore.selectedPath).toBeNull();
		expect(diffStore.selectedFile).toBeUndefined();
	});

	it('setFiles populates store and auto-selects first file', () => {
		diffStore.setFiles(mockFiles);

		expect(diffStore.files).toHaveLength(2);
		expect(diffStore.selectedPath).toBe('src/a.ts');
		expect(diffStore.selectedFile?.path).toBe('src/a.ts');
	});

	it('selectFile changes the selected file', () => {
		diffStore.setFiles(mockFiles);
		diffStore.selectFile('src/b.ts');

		expect(diffStore.selectedPath).toBe('src/b.ts');
		expect(diffStore.selectedFile?.path).toBe('src/b.ts');
	});

	it('fetchDiff calls API and populates store', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ files: mockFiles })
			})
		);

		await diffStore.fetchDiff();

		expect(diffStore.files).toHaveLength(2);
		expect(fetch).toHaveBeenCalledWith('/api/diff');

		vi.unstubAllGlobals();
	});

	it('fetchDiff throws on non-ok response', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: false,
				status: 500
			})
		);

		await expect(diffStore.fetchDiff()).rejects.toThrow('Failed to fetch diff: 500');

		vi.unstubAllGlobals();
	});
});
