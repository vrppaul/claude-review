import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { diffResponse } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const SINCE_ROUND_ONE = 'changes since round 1';
// How long the news of a retake stays up on its own
const RETAKEN_SHOWN_FOR = 12_000;

/** The rendered sentence, without the template's line breaks. */
function text(element: HTMLElement): string {
	return element.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

describe('when the tree moves under the review', () => {

	it('says so, and leaves the taking to the reader', () => {
		review.diff.treeMoved.note(3);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('tree-moved'))).toContain('3 files have changed');
		expect(getByTestId('retake-diff')).toBeTruthy();
	});

	it('does not say again what the reader has already waved away', () => {
		review.diff.treeMoved.note(3);
		review.diff.treeMoved.dismiss();

		// The same count arriving again — a reload, or the next diff fetched
		// for another base — is the same news, already dismissed
		review.diff.treeMoved.note(3);
		const { queryByTestId } = render(DiffNotice, inReview(review));

		expect(queryByTestId('tree-moved')).toBeNull();
	});

	it('says so again once more files move', () => {
		review.diff.treeMoved.note(3);
		review.diff.treeMoved.dismiss();

		review.diff.treeMoved.note(4);
		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('tree-moved'))).toContain('4 files have changed');
	});

	it('says nothing while nothing has moved', () => {
		const { queryByTestId } = render(DiffNotice, inReview(review));

		expect(queryByTestId('tree-moved')).toBeNull();
	});

	it('takes the diff again when the reader asks for it', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		server.answer('POST /api/retake', { file_count: 1, round: 2, changes: { since_round: 1, base_key: 'round:1', paths: [] } });
		review.diff.treeMoved.note(1);

		const { getByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('retake-diff'));

		expect(server.requests).toMatchObject([{ method: 'POST', path: '/api/retake' }]);
	});

	it('stays dismissed until something moves again', async () => {
		const user = userEvent.setup({ delay: null });
		review.diff.treeMoved.note(2);

		const { getByTestId, queryByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('dismiss-moved'));

		expect(queryByTestId('tree-moved')).toBeNull();
	});

	it('says what a retake did to the threads', () => {
		review.noteRetake({ followed: 2, outdated: 1 }, null);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('diff-retaken'))).toContain('2 threads followed their lines');
		expect(text(getByTestId('diff-retaken'))).toContain('1 is outdated');
	});

	it('takes the retaken bar away on its own', async () => {
		vi.useFakeTimers();
		try {
			review.noteRetake({ followed: 1, outdated: 0 }, null);
			const { queryByTestId } = render(DiffNotice, inReview(review));
			expect(queryByTestId('diff-retaken')).toBeTruthy();

			await vi.advanceTimersByTimeAsync(RETAKEN_SHOWN_FOR);

			expect(queryByTestId('diff-retaken')).toBeNull();
		} finally {
			vi.useRealTimers();
		}
	});

	it('offers a way to the thread that lost its lines', () => {
		review.threads.add(newComment({ file: 'a.py', body: 'this one' }));
		review.threads.all[0].anchor.outdated = true;
		review.noteRetake({ followed: 0, outdated: 1 }, null);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(getByTestId('show-outdated')).toBeTruthy();
	});
});

describe('threads the base on screen cannot draw', () => {

	it('lists them, so a count is not the end of the road', async () => {
		const user = userEvent.setup({ delay: null });
		serveNarrowed();
		await review.diff.setBase('round:1');
		review.threads.add(
			newComment({ file: 'elsewhere.py', startLine: 12, body: 'this one is not on this screen' })
		);

		const { getByTestId } = render(DiffNotice, inReview(review));
		expect(text(getByTestId('narrowed-to'))).toContain('1 thread is not on this screen');

		await user.click(getByTestId('list-off-screen'));

		expect(text(getByTestId('off-screen-list'))).toContain('this one is not on this screen');
		expect(text(getByTestId('off-screen-list'))).toContain('elsewhere.py');
	});

	it('lists them once, even while a retake is being reported', async () => {
		const user = userEvent.setup({ delay: null });
		serveNarrowed();
		await review.diff.setBase('round:1');
		review.threads.add(newComment({ file: 'elsewhere.py', body: 'not on this screen' }));
		review.noteRetake({ followed: 0, outdated: 0 }, { since_round: 1, base_key: 'round:1', paths: [] });

		const { getByTestId, getAllByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('list-off-screen'));

		expect(getAllByTestId('off-screen-list')).toHaveLength(1);
	});

	it('starts folded on the next narrowed base, whatever was open on the last', async () => {
		const user = userEvent.setup({ delay: null });
		serveNarrowed();
		await review.diff.setBase('round:1');
		review.threads.add(newComment({ file: 'elsewhere.py', body: 'not on this screen' }));
		const { getByTestId, queryByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('list-off-screen'));

		await review.diff.setBase('review');
		await review.diff.setBase('round:1');
		await new Promise((settle) => setTimeout(settle));

		expect(queryByTestId('off-screen-list')).toBeNull();
	});
});

/** The server answering every diff with an empty one, compared against round 1. */
function serveNarrowed() {
	fakeServer().answer('GET /api/diff', diffResponse({ phrase: SINCE_ROUND_ONE }));
}
