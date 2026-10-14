import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { diffFile, diffResponse, hunk, removedLine, sinceRound } from '../diff';
import { fakeServer, SERVER_ERROR } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';
import { settled } from '../settled';

let review: Review;

beforeEach(() => {
	review = openReview();
});

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

	it('says of one file that it has changed, not that they have', () => {
		review.diff.treeMoved.note(1);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('tree-moved'))).toContain('1 file has changed');
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
		server.answer('POST /api/retake', {
			file_count: 1,
			round: 2,
			changes: { since_round: 1, base_key: 'round:1', paths: [] }
		});
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

	it('offers a way to the thread that lost its lines, by what it is', () => {
		review.threads.add(newComment({ file: 'a.py', body: 'this one' }));
		review.threads.all[0].anchor.outdated = true;
		review.noteRetake({ followed: 0, outdated: 1 }, null);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('show-outdated'))).toBe('Show the outdated thread');
	});

	it('offers a way to the first of several threads that lost their lines', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'this one' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'and this one' }));
		for (const thread of review.threads.all) thread.anchor.outdated = true;
		review.noteRetake({ followed: 0, outdated: 2 }, null);

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('show-outdated'))).toBe('Show the first outdated thread');
	});
});

describe('threads the base on screen cannot draw', () => {
	it('lists them, so a count is not the end of the road', async () => {
		const user = userEvent.setup({ delay: null });
		serveNarrowed();
		await review.diff.setBase('round:1');
		review.threads.add(newComment({ file: 'elsewhere.py', startLine: 12, body: 'this one is not on this screen' }));

		const { getByTestId } = render(DiffNotice, inReview(review));
		expect(text(getByTestId('narrowed-to'))).toContain('1 thread is not on this screen');
		expect(text(getByTestId('list-off-screen'))).toBe('List it');

		await user.click(getByTestId('list-off-screen'));
		expect(text(getByTestId('list-off-screen'))).toBe('Hide it');

		expect(text(getByTestId('off-screen-list'))).toContain('this one is not on this screen');
		expect(text(getByTestId('off-screen-list'))).toContain('elsewhere.py');
	});

	it('lists each by its first words, plainly', async () => {
		const user = userEvent.setup({ delay: null });
		serveNarrowed();
		await review.diff.setBase('round:1');
		review.threads.add(newComment({ file: 'elsewhere.py', startLine: 12, body: '**Rename** `x`, please' }));

		const { getByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('list-off-screen'));

		expect(text(getByTestId('off-screen-thread'))).toContain('Rename x, please');
	});

	it("counts a thread on a removed line, whose number belongs to the base's left side", async () => {
		const shown = diffFile({ path: 'a.py', hunks: [hunk([removedLine(3, 'gone')])] });
		fakeServer().answer('GET /api/diff', diffResponse({ base: sinceRound(1), files: [shown] }));
		await review.diff.setBase('round:1');
		review.threads.add(newComment({ file: 'a.py', side: 'old', startLine: 3, body: 'on a removed line' }));

		const { getByTestId } = render(DiffNotice, inReview(review));

		expect(text(getByTestId('narrowed-to'))).toContain('1 thread is not on this screen');
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
		await settled();

		expect(queryByTestId('off-screen-list')).toBeNull();
	});
});

describe('a bar that could not do what it was asked', () => {
	it('says why in that bar, and in no other on the screen', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ base: sinceRound(1) }));
		server.refuse('POST /api/retake', SERVER_ERROR, 'The repository is locked');
		await review.diff.setBase('round:1');
		review.diff.treeMoved.note(1);

		const { getByTestId, findByTestId, queryByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('retake-diff'));

		expect(text(await findByTestId('retake-error'))).toContain('The repository is locked');
		expect(getByTestId('narrowed-to')).toBeTruthy();
		expect(queryByTestId('narrow-error')).toBeNull();
	});

	it('says a failure to show the whole diff in the narrowed bar alone', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		server.refuse('GET /api/diff', SERVER_ERROR, 'The diff could not be read');
		review.diff.treeMoved.note(1);

		const { getByTestId, findByTestId, queryByTestId } = render(DiffNotice, inReview(review));
		await user.click(getByTestId('show-everything'));

		expect(text(await findByTestId('narrow-error'))).toContain('The diff could not be read');
		expect(queryByTestId('retake-error')).toBeNull();
	});
});

/** The server answering every diff with an empty one, compared against round 1. */
function serveNarrowed() {
	fakeServer().answer('GET /api/diff', diffResponse({ base: sinceRound(1) }));
}
