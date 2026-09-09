import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileList from '$lib/components/FileList.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { registerSection } from '$lib/utils/scroll';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const diffFiles: DiffFile[] = [
	{
		path: 'src/handler.ts',
		status: 'modified',
		is_binary: false,
		old_mode: null,
		new_mode: null,
		hunks: [
			{
				header: '@@ -1,2 +1,3 @@',
				old_start: 1,
				new_start: 1,
				lines: [
					{ type: 'add', old_no: null, new_no: 1, content: 'new line' },
					{ type: 'delete', old_no: 1, new_no: null, content: 'old line' }
				]
			}
		]
	},
	{
		path: 'src/utils.ts',
		status: 'added',
		is_binary: false,
		old_mode: null,
		new_mode: null,
		hunks: []
	}
];

const textFiles: DiffFile[] = [
	{
		path: '/tmp/plan.md',
		status: 'added',
		is_binary: false,
		old_mode: null,
		new_mode: null,
		hunks: [
			{
				header: '',
				old_start: 0,
				new_start: 1,
				lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Plan' }]
			}
		]
	}
];

describe('FileList', () => {
	beforeEach(() => {
		commentStore.clear();
	});

	it('shows file count in header', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId } = render(FileList);
		const header = getByTestId('sidebar-heading');

		expect(header?.textContent).toContain('2');
	});

	it('counts what is being reviewed, in words', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId } = render(FileList);

		expect(getByTestId('sidebar-heading').textContent).toBe('2 changed files');
	});

	it('names plain files as files rather than changes', () => {
		diffStore.setFiles(textFiles, 'files');

		const { getByTestId } = render(FileList);

		expect(getByTestId('sidebar-heading').textContent).toBe('1 file');
	});

	it('counts how many files are done once any are', async () => {
		diffStore.setFiles(diffFiles, 'diff');
		diffStore.setViewed('src/handler.ts', true);

		const { getByTestId } = render(FileList);

		expect(getByTestId('sidebar-heading').textContent).toBe('2 changed files · 1 viewed');
	});

	it('renders file items', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getAllByTestId } = render(FileList);
		const items = getAllByTestId('file-item');

		expect(items).toHaveLength(2);
	});

	it('takes the reader to the file it names', async () => {
		diffStore.setFiles(diffFiles, 'diff');
		const section = document.createElement('div');
		const scrollIntoView = vi.fn();
		section.scrollIntoView = scrollIntoView;
		const unregister = registerSection('src/utils.ts', section);

		const { getAllByTestId } = render(FileList);
		await userEvent.click(getAllByTestId('file-item')[1]);

		expect(scrollIntoView).toHaveBeenCalled();
		unregister();
	});

	it('marks a file the reader has finished with', () => {
		diffStore.setFiles(diffFiles, 'diff');
		diffStore.setViewed('src/handler.ts', true);

		const { getAllByTestId } = render(FileList);

		expect(getAllByTestId('file-viewed-mark')).toHaveLength(1);
	});

	it('shows "Messages" header in transcript mode', () => {
		const transcriptFiles: DiffFile[] = [
			{
				path: 'user-1',
				status: 'added',
				is_binary: false,
				old_mode: null,
				new_mode: null,
				hunks: [
					{
						header: '',
						old_start: 0,
						new_start: 1,
						lines: [{ type: 'context', old_no: null, new_no: 1, content: 'hello' }]
					}
				]
			},
			{
				path: 'assistant-2',
				status: 'added',
				is_binary: false,
				old_mode: null,
				new_mode: null,
				hunks: [
					{
						header: '',
						old_start: 0,
						new_start: 1,
						lines: [{ type: 'context', old_no: null, new_no: 1, content: 'hi' }]
					}
				]
			}
		];
		diffStore.setFiles(transcriptFiles, 'transcript');

		const { getByTestId, getAllByTestId, getByText } = render(FileList);
		const header = getByTestId('sidebar').querySelector('h2');

		expect(header?.textContent).toBe('2 messages');
		expect(getAllByTestId('file-item')).toHaveLength(2);
	});
});

describe('finding a file in a long review', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
	});

	it('narrows the list to paths that match', async () => {
		const user = userEvent.setup();
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId, getAllByTestId } = render(FileList);
		await user.type(getByTestId('file-filter'), 'utils');

		const items = getAllByTestId('file-item');
		expect(items).toHaveLength(1);
		expect(items[0].textContent).toContain('utils.ts');
	});

	it('says so when nothing matches', async () => {
		const user = userEvent.setup();
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId, queryAllByTestId } = render(FileList);
		await user.type(getByTestId('file-filter'), 'zzz');

		expect(queryAllByTestId('file-item')).toHaveLength(0);
		expect(getByTestId('no-matches')).toBeTruthy();
	});

	it('reports how many of the files are showing while filtering', async () => {
		const user = userEvent.setup();
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId } = render(FileList);
		await user.type(getByTestId('file-filter'), 'utils');

		expect(getByTestId('sidebar-heading').textContent).toBe('1 of 2');
	});

	it('folds a directory away and back', async () => {
		const user = userEvent.setup();
		diffStore.setFiles(diffFiles, 'diff');

		const { getAllByTestId, queryAllByTestId } = render(FileList);
		expect(queryAllByTestId('file-item')).toHaveLength(2);

		await user.click(getAllByTestId('folder-item')[0]);
		expect(queryAllByTestId('file-item')).toHaveLength(0);

		await user.click(getAllByTestId('folder-item')[0]);
		expect(queryAllByTestId('file-item')).toHaveLength(2);
	});
});
