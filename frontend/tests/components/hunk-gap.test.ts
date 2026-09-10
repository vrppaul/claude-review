import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { expansionStore } from '$lib/stores/expansions.svelte';
import type { DiffFile } from '$lib/types';

const file: DiffFile = {
	path: 'src/app.py',
	status: 'modified',
	hunks: [
		{
			header: '@@ -30,2 +30,2 @@',
			old_start: 30,
			new_start: 30,
			lines: [
				{ type: 'delete', old_no: 30, new_no: null, content: 'x = 1' },
				{ type: 'add', old_no: null, new_no: 30, content: 'x = 2' }
			]
		}
	],
	is_binary: false,
	old_mode: null,
	new_mode: null
};

describe('widening the context around a hunk', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		expansionStore.clear();
		diffStore.setFiles([file], 'diff');
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('offers to show the lines the diff left out', () => {
		const { getByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('expand-context').textContent).toContain('29 hidden lines');
	});

	it('reads the lines and shows them above the hunk', async () => {
		const user = userEvent.setup();
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ start: 10, lines: ['before one', 'before two'], total: 40 })
			})
		);

		const { getByTestId, getByText } = render(FileSection, { props: { file } });
		await user.click(getByTestId('expand-context'));

		expect(getByText('before one')).toBeTruthy();
		expect(getByText('before two')).toBeTruthy();
	});

	it('takes a gap this small in one go', async () => {
		const user = userEvent.setup();
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ start: 10, lines: [], total: 40 })
		});
		vi.stubGlobal('fetch', fetchMock);

		const { getByTestId } = render(FileSection, { props: { file } });
		await user.click(getByTestId('expand-context'));

		const url = fetchMock.mock.calls[0][0] as string;
		expect(url).toContain('path=src%2Fapp.py');
		expect(url).toContain('start=1');
		expect(url).toContain('end=29');
	});

	it('reveals a large gap a piece at a time', async () => {
		const user = userEvent.setup();
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ start: 481, lines: [], total: 900 })
		});
		vi.stubGlobal('fetch', fetchMock);

		const distant: DiffFile = {
			...file,
			path: 'src/long.py',
			hunks: [{ ...file.hunks[0], new_start: 501, old_start: 501 }]
		};
		diffStore.setFiles([distant], 'diff');

		const { getByTestId } = render(FileSection, { props: { file: distant } });
		expect(getByTestId('expand-context').textContent).toContain('of 500 hidden lines');

		await user.click(getByTestId('expand-context'));

		const url = fetchMock.mock.calls[0][0] as string;
		expect(url).toContain('start=481');
		expect(url).toContain('end=500');
	});

	it('says so when the file could not be read', async () => {
		const user = userEvent.setup();
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 400 }));

		const { getByTestId } = render(FileSection, { props: { file } });
		await user.click(getByTestId('expand-context'));

		expect(getByTestId('expand-error')).toBeTruthy();
	});

	it('offers nothing when the hunk already starts at the top of the file', () => {
		const fromTop: DiffFile = {
			...file,
			path: 'src/top.py',
			hunks: [{ ...file.hunks[0], new_start: 1, old_start: 1 }]
		};
		diffStore.setFiles([fromTop], 'diff');

		const { queryByTestId } = render(FileSection, { props: { file: fromTop } });

		expect(queryByTestId('hunk-gap')).toBeNull();
	});

	it('leaves plain files alone, since nothing of them is hidden', () => {
		const plain: DiffFile = { ...file, path: '/tmp/plan.md' };
		diffStore.setFiles([plain], 'files');

		const { queryByTestId } = render(FileSection, { props: { file: plain } });

		expect(queryByTestId('hunk-gap')).toBeNull();
	});

	it('takes the jump marker away once nothing is hidden any more', async () => {
		const user = userEvent.setup();
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () =>
					Promise.resolve({
						start: 1,
						lines: Array.from({ length: 29 }, (_, i) => `line ${i + 1}`),
						total: 40
					})
			})
		);
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });
		expect(getByTestId('hunk-header')).toBeTruthy();

		await user.click(getByTestId('expand-context'));

		// The code now runs from the top of the file into the hunk without a
		// break, and a marker saying otherwise is punctuation mid-sentence
		expect(queryByTestId('hunk-header')).toBeNull();
		expect(queryByTestId('hunk-gap')).toBeNull();
	});
});
