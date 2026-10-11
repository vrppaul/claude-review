import { describe, it, expect } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import RepliesMenu from '$lib/components/RepliesMenu.svelte';
import { lineAnchor } from '$lib/anchors/line';
import { addedLine, contextLine, diffFile, hunk } from '../diff';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

// What someone who cannot see the page is told about it, read off the
// accessible tree as a screen reader reads it: roles and names
const files = [
	diffFile({ path: 'src/a.py', hunks: [hunk([contextLine(1, 1, 'x = 1'), addedLine(2, 'y = 2')])] }),
	diffFile({ path: 'src/b.py', hunks: [hunk([addedLine(1, 'z = 3')])] })
];

/** A review an agent answers, its panel open beside the diff. */
function openedReview() {
	const review = openReview({ files, facts: { answerer_attached: true } });
	review.layout.agentPanel.setOpen(true);
	return review;
}

describe('the review, as a screen reader reads it', () => {
	it('has a main part, the diff, beside a named file tree and a named agent panel', () => {
		const { getByRole } = render(ReviewScreen, { props: { review: openedReview() } });

		expect(getByRole('main')).toBeTruthy();
		expect(getByRole('complementary', { name: 'Files' })).toBeTruthy();
		expect(getByRole('complementary', { name: 'The agent' })).toBeTruthy();
	});

	it('heads each file with its path, and names each Viewed box with the file it marks', () => {
		const { getByRole } = render(ReviewScreen, { props: { review: openedReview() } });

		for (const { path } of files) {
			expect(getByRole('heading', { name: path })).toBeTruthy();
			expect(getByRole('checkbox', { name: `Viewed: ${path}` })).toBeTruthy();
		}
	});

	it('names each thread by where it hangs', () => {
		const review = openedReview();
		review.threads.add(newComment({ file: 'src/a.py', startLine: 2, body: 'Why 2?' }));

		const { getByRole } = render(ReviewScreen, { props: { review } });

		const thread = getByRole('group', { name: 'Thread on src/a.py · Line 2' });
		expect(within(thread).getByText('Why 2?')).toBeTruthy();
	});

	it('reads a line once: the number only a pointer reaches is left unsaid', () => {
		const { getByRole } = render(ReviewScreen, { props: { review: openedReview() } });

		// The unchanged line has a number on each side, the same line twice
		const section = getByRole('heading', { name: 'src/a.py' }).closest('section');
		expect(within(section as HTMLElement).getAllByRole('button', { name: 'Comment on line 1' })).toHaveLength(1);
	});

	it('reads the conversation with the agent as a log, and says what arrives from it aloud', () => {
		const review = openedReview();
		review.threads.add(newComment({ file: 'src/a.py', startLine: 2, body: 'Why 2?' }));
		const { getByRole } = render(ReviewScreen, { props: { review } });
		expect(getByRole('log', { name: 'Conversation with the agent' })).toBeTruthy();
		expect(getByRole('status').textContent?.trim()).toBe('');

		review.threads.receiveReply(review.threads.all[0].id, 'Because 1 is taken', null);
		review.threads.raise('raised-1', lineAnchor('src/b.py', 'new', 1, 1, ['z = 3']), 'On purpose?', 'question');
		flushSync();

		expect(getByRole('status').textContent?.trim()).toBe('2 new from the agent, not read yet');
	});

	it('makes the grips that size a column splitters that say how wide it is', () => {
		const review = openedReview();
		const { getByRole } = render(ReviewScreen, { props: { review } });

		const grip = getByRole('separator', { name: 'Resize the file tree' });
		expect(grip.getAttribute('aria-valuenow')).toBe(String(review.layout.fileTree.width));
		expect(grip.getAttribute('aria-valuemin')).toBe(String(review.layout.fileTree.least));
		expect(grip.getAttribute('aria-valuemax')).toBe(String(review.layout.fileTree.most));
		expect(getByRole('separator', { name: 'Resize the panel' })).toBeTruthy();
	});

	it('says which replies are unread, not only with a dot', async () => {
		const user = userEvent.setup({ delay: null });
		const review = openedReview();
		review.threads.add(newComment({ file: 'src/a.py', startLine: 2, body: 'Why 2?' }));
		review.threads.receiveReply(review.threads.all[0].id, 'Because 1 is taken', null);

		const { getByTestId, getByRole } = render(RepliesMenu, inReview(review));
		await user.click(getByTestId('replies-menu'));

		expect(getByRole('button', { name: /^unread:/ })).toBeTruthy();
	});
});
