import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import RepliesMenu from '$lib/components/RepliesMenu.svelte';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

/** A review with one thread the agent has answered, in these words. */
function answered(answer: string) {
	const review = openReview({ facts: { answerer_attached: true } });
	review.threads.add(newComment({ file: 'src/a.py', startLine: 2, body: 'Why 2?' }));
	review.threads.receiveReply(review.threads.all[0].id, answer, null);
	return review;
}

describe('the list of replies', () => {
	it("says each thread's last answer in plain words, not in its Markdown", async () => {
		const user = userEvent.setup({ delay: null });
		const review = answered('**Because** `1` is [taken](https://example.com).');

		const { getByTestId } = render(RepliesMenu, inReview(review));
		await user.click(getByTestId('replies-menu'));

		expect(getByTestId('reply-row').textContent).toContain('Because 1 is taken.');
	});

	it('offers to mark everything read only while something is unread', async () => {
		const user = userEvent.setup({ delay: null });
		const review = answered('Because 1 is taken.');

		const { getByTestId } = render(RepliesMenu, inReview(review));
		await user.click(getByTestId('replies-menu'));
		expect((getByTestId('mark-all-read') as HTMLButtonElement).disabled).toBe(false);

		await user.click(getByTestId('mark-all-read'));
		expect((getByTestId('mark-all-read') as HTMLButtonElement).disabled).toBe(true);
	});
});
