import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const file: DiffFile = {
	path: 'src/app.ts',
	status: 'modified',
	hunks: [
		{
			header: '@@ -1,3 +1,3 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'const a = 1;' },
				{ type: 'delete', old_no: 2, new_no: null, content: 'const b = 2;' },
				{ type: 'add', old_no: null, new_no: 2, content: 'const b = 3;' },
				{ type: 'add', old_no: null, new_no: 3, content: 'const c = 4;' }
			]
		}
	],
	is_binary: false,
	old_mode: null,
	new_mode: null
};

describe('split layout', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		diffStore.setFiles([file], 'diff');
	});

	it('reads down one column until asked for two', () => {
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('split-view')).toBeNull();
	});

	it('faces the old version against the new one', () => {
		diffStore.setDiffLayout('split');

		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('split-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('shows both versions of a replaced line on one row', () => {
		diffStore.setDiffLayout('split');

		const { getByTestId } = render(FileSection, { props: { file } });
		const rows = getByTestId('split-view').querySelectorAll('tbody > tr');
		const replaced = rows[1].textContent ?? '';

		expect(replaced).toContain('const b = 2;');
		expect(replaced).toContain('const b = 3;');
	});

	it('leaves the old side of a pure insertion empty', () => {
		diffStore.setDiffLayout('split');

		const { getByTestId } = render(FileSection, { props: { file } });
		const cells = getByTestId('split-view').querySelectorAll('tbody > tr')[2].querySelectorAll('td');

		expect(cells[1].textContent?.trim()).toBe('');
		expect(cells[3].textContent).toContain('const c = 4;');
	});

	it('files a comment left on the old side as a removal', async () => {
		const user = userEvent.setup();
		diffStore.setDiffLayout('split');

		const { getByTestId } = render(FileSection, { props: { file } });
		const oldGutter = getByTestId('split-view')
			.querySelectorAll('tbody > tr')[1]
			.querySelector('button')!;

		await user.click(oldGutter);
		await user.click(document.body);
		await user.type(getByTestId('comment-input'), 'why did this go');
		await user.click(getByTestId('save-comment'));

		expect(commentStore.comments[0].side).toBe('old');
		expect(commentStore.comments[0].start_line).toBe(2);
	});

	it('keeps a comment made in one layout visible in the other', async () => {
		commentStore.add('src/app.ts', 'new', 2, 2, 'tighten this');
		diffStore.setDiffLayout('split');

		const { getByText } = render(FileSection, { props: { file } });

		expect(getByText('tighten this')).toBeTruthy();
	});
});
