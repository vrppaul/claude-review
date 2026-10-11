import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import { openReview } from '../review';

const files = [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x = 1')])] })];

describe('comments picked up from before a reload', () => {
	it('are said once, until the reader puts the notice away', async () => {
		const user = userEvent.setup();
		openReview({ files }).threads.add(newComment({ file: 'a.py', body: 'kept' }));
		const review = openReview({ files });

		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review } });
		expect(getByTestId('restored-notice').textContent).toContain('Picked up 1 comment you had not sent yet.');

		await user.click(getByTestId('dismiss-restored'));

		expect(queryByTestId('restored-notice')).toBeNull();
	});
});

describe('a diff with nothing in it', () => {
	it('says so where the files were, and leaves the review around it', async () => {
		const review = openReview({ files, facts: { answerer_attached: true } });
		review.layout.agentPanel.setOpen(true);
		const { getByTestId } = render(ReviewScreen, { props: { review } });

		// The agent undid its work and took the diff again: nothing differs from the base any more
		fakeServer().answer('GET /api/diff', diffResponse({ files: [] }));
		await review.diff.take();
		await tick();

		expect(getByTestId('diff-view').textContent).toContain('No changes found.');
		expect(getByTestId('top-bar')).toBeTruthy();
		expect(getByTestId('quick-submit')).toBeTruthy();
		expect(getByTestId('agent-panel')).toBeTruthy();
	});
});
