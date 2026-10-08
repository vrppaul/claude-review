import { describe, it, expect, beforeEach } from 'vitest';
import { userEvent } from '@testing-library/user-event';
import { render } from '@testing-library/svelte';
import SubmitBar from '$lib/components/SubmitBar.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { contextLine, diffFile, hunk } from '../diff';
import { newComment } from '../new-comment';

const file = diffFile({ path: 'test.py', hunks: [hunk([contextLine(1, 1, 'hello')])] });

describe('sending the review', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff');
	});

	it('counts the comments written', () => {
		commentStore.add(newComment({ file: 'test.py', body: 'fix' }));
		commentStore.add(newComment({ file: 'test.py', startLine: 2, body: 'fix2' }));

		const { getByTestId } = render(SubmitBar);
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('2');
		expect(count.textContent).toContain('comments');
	});

	it('says one comment, not one comments', () => {
		commentStore.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar);
		const count = getByTestId('comment-count');

		expect(count.textContent).toContain('1');
		expect(count.textContent).toMatch(/\bcomment\b/);
	});

	it('can be opened once something is written', () => {
		commentStore.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar);

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});

	it('opens even with nothing written, because a summary alone is a review', () => {
		const { getByTestId } = render(SubmitBar);

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});
});

describe('the review header', () => {
	it('says what is under review', () => {
		diffStore.setFiles([file], 'diff', 'claude-review: uncommitted changes');

		const { getByTestId } = render(SubmitBar);

		expect(getByTestId('review-title').textContent?.trim()).toBe(
			'claude-review: uncommitted changes'
		);
	});

	it('leaves the title out when the server sent none', () => {
		diffStore.setFiles([file], 'diff');

		const { queryByTestId } = render(SubmitBar);

		expect(queryByTestId('review-title')).toBeNull();
	});

	it('offers comment navigation only once there is a comment', async () => {
		diffStore.setFiles([file], 'diff');

		const { queryByTestId, rerender } = render(SubmitBar);
		expect(queryByTestId('next-comment')).toBeNull();

		commentStore.add(newComment({ file: 'test.py', body: 'fix' }));
		await rerender({});

		expect(queryByTestId('next-comment')).toBeTruthy();
	});

	it('opens one door to everything that ends a round', async () => {
		const user = userEvent.setup({ delay: null });
		commentStore.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(SubmitBar);
		await user.click(getByTestId('quick-submit'));

		// What was written, a summary, and the two ways out — all in one place
		expect(getByTestId('finish-review')).toBeTruthy();
		expect(getByTestId('finish-comment')).toBeTruthy();
		expect(getByTestId('review-body')).toBeTruthy();
		expect(getByTestId('modal-submit')).toBeTruthy();
	});
});
