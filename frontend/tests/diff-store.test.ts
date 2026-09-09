import { describe, it, expect, beforeEach, vi } from 'vitest';
import { diffStore } from '$lib/stores/diff.svelte';
import type { DiffFile } from '$lib/types';

const mockFiles: DiffFile[] = [
	{
		path: 'src/a.ts',
		status: 'modified',
		is_binary: false,
		old_mode: null,
		new_mode: null,
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
		is_binary: false,
		old_mode: null,
		new_mode: null,
		hunks: []
	}
];

describe('diffStore', () => {
	beforeEach(() => {
		diffStore.clear();
	});

	it('starts with empty files', () => {
		expect(diffStore.files).toEqual([]);
		expect(diffStore.selectedPath).toBeNull();
		expect(diffStore.selectedFile).toBeUndefined();
	});

	it('setFiles populates store and auto-selects first file', () => {
		diffStore.setFiles(mockFiles, 'diff');

		expect(diffStore.files).toHaveLength(2);
		expect(diffStore.selectedPath).toBe('src/a.ts');
		expect(diffStore.selectedFile?.path).toBe('src/a.ts');
	});

	it('records the file scrolled into view', () => {
		diffStore.setFiles(mockFiles, 'diff');
		diffStore.markInView('src/b.ts');

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

	it('mode defaults to diff', () => {
		expect(diffStore.mode).toBe('diff');
	});

	it('setFiles with mode updates the mode', () => {
		diffStore.setFiles(mockFiles, 'files');

		expect(diffStore.mode).toBe('files');
	});

	it('clear resets mode to diff', () => {
		diffStore.setFiles(mockFiles, 'files');
		diffStore.clear();

		expect(diffStore.mode).toBe('diff');
	});

	it('fetchDiff captures mode from API response', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ files: mockFiles, mode: 'files' })
			})
		);

		await diffStore.fetchDiff();

		expect(diffStore.mode).toBe('files');

		vi.unstubAllGlobals();
	});

	it('setFiles with transcript mode updates the mode', () => {
		diffStore.setFiles(mockFiles, 'transcript');

		expect(diffStore.mode).toBe('transcript');
	});

	it('contentViewMode defaults to raw', () => {
		expect(diffStore.contentViewMode).toBe('raw');
	});

	it('setContentViewMode updates the view mode', () => {
		diffStore.setContentViewMode('preview');

		expect(diffStore.contentViewMode).toBe('preview');
	});

	it('keeps how a file is shown across reviews — it is the reader, not the review', () => {
		diffStore.setContentViewMode('side-by-side');
		diffStore.clear();

		expect(diffStore.contentViewMode).toBe('side-by-side');
	});
});

describe('retaking the diff', () => {
	beforeEach(() => {
		diffStore.clear();
		vi.unstubAllGlobals();
	});

	it('asks git to leave whitespace-only changes out', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ files: [], mode: 'diff', title: 'repo' })
		});
		vi.stubGlobal('fetch', fetchMock);

		await diffStore.setIgnoreWhitespace(true);

		expect(fetchMock).toHaveBeenCalledWith('/api/diff?ignore_whitespace=true');
		expect(diffStore.ignoreWhitespace).toBe(true);
	});

	it('keeps the files already worked through', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ files: [], mode: 'diff', title: 'repo' })
			})
		);
		diffStore.setViewed('src/a.ts', true);

		await diffStore.setIgnoreWhitespace(true);

		// Retaking the diff must not undo a reader's progress through it
		expect(diffStore.isViewed('src/a.ts')).toBe(true);
	});
});

describe('the choices a reader makes about how a review is drawn', () => {
	beforeEach(() => {
		localStorage.clear();
		diffStore.clear();
	});

	it('remembers the layout', () => {
		diffStore.setDiffLayout('split');

		expect(localStorage.getItem('claude-review:layout')).toBe('split');
	});

	it('remembers how a markdown file is shown', () => {
		diffStore.setContentViewMode('side-by-side');

		expect(localStorage.getItem('claude-review:content-view')).toBe('side-by-side');
	});

	it('keeps them across a review, which is not what they belong to', () => {
		diffStore.setDiffLayout('split');

		diffStore.clear();

		expect(diffStore.diffLayout).toBe('split');
	});

	it('ignores a stored choice that is no longer a choice', () => {
		localStorage.setItem('claude-review:layout', 'three-columns');

		diffStore.clear();

		expect(diffStore.diffLayout).toBe('unified');
	});
});
