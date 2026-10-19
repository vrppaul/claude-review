import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { REVIEW_TITLE, contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import { openReview } from '../review';
import { DRAFT_SHAPE } from '$lib/drafts/draft-shapes';
import { DRAFT_KEY, storeDraft, storeReleasedDraft } from '../stored-draft';

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

describe('a kept draft that could not be read', () => {
	it('is said to be set aside, once, and the review opens without it', async () => {
		const user = userEvent.setup();
		storeReleasedDraft({ title: REVIEW_TITLE, reviewBody: '', comments: [null] });
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
		const review = openReview({ files });

		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review } });

		expect(review.threads.all).toEqual([]);
		expect(getByTestId('draft-set-aside').textContent).toContain('A kept draft could not be read; it is set aside.');

		await user.click(getByTestId('dismiss-set-aside'));

		expect(queryByTestId('draft-set-aside')).toBeNull();
	});
});

describe('a kept draft that reads but cannot be opened', () => {
	it('is set aside as one that cannot be read is, said once, and the review opens without it', () => {
		// The current shape by its number, with nothing else a review opens on
		storeDraft({ version: DRAFT_SHAPE, threads: [] });
		const asItWasKept = localStorage.getItem(DRAFT_KEY);
		const told = vi.spyOn(console, 'error').mockImplementation(() => undefined);

		const review = openReview({ files });
		const { getByTestId } = render(ReviewScreen, { props: { review } });

		expect(review.threads.all).toEqual([]);
		expect(getByTestId('draft-set-aside').textContent).toContain('A kept draft could not be read; it is set aside.');
		expect(localStorage.getItem(`${DRAFT_KEY}:unreadable:1`)).toBe(asItWasKept);
		expect(told).toHaveBeenCalledWith(expect.any(String), expect.any(TypeError));
	});

	it('locks nobody out: the next page opens on no draft, with nothing more to say', () => {
		storeDraft({ version: DRAFT_SHAPE, threads: [] });
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
		openReview({ files });

		const review = openReview({ files });
		const { queryByTestId } = render(ReviewScreen, { props: { review } });

		expect(queryByTestId('draft-set-aside')).toBeNull();
	});
});

describe('comments picked up from a review sent in rounds', () => {
	it('counts only what had not gone out, as the header counts what is unsent, and stands under the header', () => {
		const before = openReview({ files });
		before.threads.add(newComment({ file: 'a.py', body: 'went out' }));
		before.threads.add(newComment({ file: 'a.py', body: 'kept' }));
		before.threads.markSent(before.threads.carry([before.threads.all[0]]), 1);
		const review = openReview({ files });

		const { getByTestId } = render(ReviewScreen, { props: { review } });
		const notice = getByTestId('restored-notice');

		expect(notice.textContent).toContain('Picked up 1 comment you had not sent yet.');
		expect(getByTestId('top-bar').compareDocumentPosition(notice) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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
