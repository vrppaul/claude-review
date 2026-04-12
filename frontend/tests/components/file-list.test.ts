import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileList from '$lib/components/FileList.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const diffFiles: DiffFile[] = [
	{
		path: 'src/handler.ts',
		status: 'modified',
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
		hunks: []
	}
];

const textFiles: DiffFile[] = [
	{
		path: '/tmp/plan.md',
		status: 'added',
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
		const header = getByTestId('sidebar').querySelector('h2');

		expect(header?.textContent).toContain('2');
	});

	it('shows "Changed Files" header in diff mode', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getByTestId } = render(FileList);
		const header = getByTestId('sidebar').querySelector('h2');

		expect(header?.textContent).toContain('Changed Files');
	});

	it('shows "Files" header in files mode', () => {
		diffStore.setFiles(textFiles, 'files');

		const { getByTestId } = render(FileList);
		const header = getByTestId('sidebar').querySelector('h2');

		expect(header?.textContent).toContain('Files');
		expect(header?.textContent).not.toContain('Changed');
	});

	it('renders file items', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getAllByTestId } = render(FileList);
		const items = getAllByTestId('file-item');

		expect(items).toHaveLength(2);
	});

	it('clicking a file item selects it', async () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getAllByTestId } = render(FileList);
		const items = getAllByTestId('file-item');

		await userEvent.click(items[1]);

		expect(diffStore.selectedPath).toBe('src/utils.ts');
	});

	it('shows mode badge', () => {
		diffStore.setFiles(diffFiles, 'diff');

		const { getByText } = render(FileList);

		expect(getByText('diff')).toBeTruthy();
	});

	it('shows different mode badge for files mode', () => {
		diffStore.setFiles(textFiles, 'files');

		const { getByText } = render(FileList);

		expect(getByText('files')).toBeTruthy();
	});
});
