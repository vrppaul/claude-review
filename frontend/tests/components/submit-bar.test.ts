import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import SubmitBar from '$lib/components/SubmitBar.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const mockFile: DiffFile = {
	path: 'test.py',
	status: 'modified',
	is_binary: false,
	old_mode: null,
	new_mode: null,
	hunks: [
		{
			header: '@@ -1 +1 @@',
			old_start: 1,
			new_start: 1,
			lines: [{ type: 'context', old_no: 1, new_no: 1, content: 'hello' }]
		}
	]
};

describe('SubmitBar', () => {
	beforeEach(() => {
		commentStore.clear();
		diffStore.setFiles([mockFile], 'diff');
	});

	it('shows comment count', () => {
		commentStore.add('test.py', 'new', 1, 1, 'fix');
		commentStore.add('test.py', 'new', 2, 2, 'fix2');

		const { getByTestId } = render(SubmitBar);
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('2');
		expect(count.textContent).toContain('comments');
	});

	it('shows singular label for one comment', () => {
		commentStore.add('test.py', 'new', 1, 1, 'fix');

		const { getByTestId } = render(SubmitBar);
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('1');
		expect(count.textContent).toMatch(/\bcomment\b/);
	});

	it('disables quick submit when no inline comments', () => {
		const { getByTestId } = render(SubmitBar);

		const btn = getByTestId('quick-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('enables quick submit when inline comments exist', () => {
		commentStore.add('test.py', 'new', 1, 1, 'fix');

		const { getByTestId } = render(SubmitBar);

		const btn = getByTestId('quick-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});

	it('finish review button is always enabled', () => {
		const { getByTestId } = render(SubmitBar);

		const btn = getByTestId('finish-review') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});
});

describe('the review header', () => {
	beforeEach(() => {
		commentStore.clear();
		diffStore.clear();
	});

	it('says what is under review', () => {
		diffStore.setFiles([mockFile], 'diff', 'claude-review: uncommitted changes');

		const { getByTestId } = render(SubmitBar);

		expect(getByTestId('review-title').textContent?.trim()).toBe(
			'claude-review: uncommitted changes'
		);
	});

	it('leaves the title out when the server sent none', () => {
		diffStore.setFiles([mockFile], 'diff');

		const { queryByTestId } = render(SubmitBar);

		expect(queryByTestId('review-title')).toBeNull();
	});

	it('offers comment navigation only once there is a comment', async () => {
		diffStore.setFiles([mockFile], 'diff');

		const { queryByTestId, rerender } = render(SubmitBar);
		expect(queryByTestId('next-comment')).toBeNull();

		commentStore.add('test.py', 'new', 1, 1, 'fix');
		await rerender({});

		expect(queryByTestId('next-comment')).toBeTruthy();
	});
});
