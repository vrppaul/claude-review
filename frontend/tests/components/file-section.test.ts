import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const file: DiffFile = {
	path: 'src/core/session.py',
	status: 'modified',
	hunks: [
		{
			header: '@@ -1,3 +1,3 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'import os' },
				{ type: 'delete', old_no: 2, new_no: null, content: 'x = 1' },
				{ type: 'add', old_no: null, new_no: 2, content: 'x = 2' }
			]
		}
	],
	is_binary: false,
	old_mode: null,
	new_mode: null
};

describe('FileSection', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		diffStore.setFiles([file], 'diff');
	});

	it('names the file and how much it changed', () => {
		const { getByText } = render(FileSection, { props: { file } });

		expect(getByText('src/core/session.py')).toBeTruthy();
		expect(getByText('+1')).toBeTruthy();
		expect(getByText('−1')).toBeTruthy();
	});

	it('folds the body away and brings it back', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(queryByTestId('raw-view')).toBeTruthy();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeNull();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('folds the file when it is marked viewed', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));

		expect(diffStore.isViewed('src/core/session.py')).toBe(true);
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('brings the file back when it is unmarked', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('viewed-toggle'));

		expect(diffStore.isViewed('src/core/session.py')).toBe(false);
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('can be reopened after being marked viewed, without unmarking it', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('collapse-file'));

		expect(queryByTestId('raw-view')).toBeTruthy();
		expect(diffStore.isViewed('src/core/session.py')).toBe(true);
	});

	it('shows how many comments the file carries', () => {
		commentStore.add('src/core/session.py', 'new', 2, 2, 'rename this');

		const { getByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('section-comment-count').textContent?.trim()).toBe('1');
	});

	it('leaves the comment count off a file with none', () => {
		const { queryByTestId } = render(FileSection, { props: { file } });

		expect(queryByTestId('section-comment-count')).toBeNull();
	});
});
