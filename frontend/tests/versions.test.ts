import { beforeEach, describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { isDrawn } from '$lib/anchors/placement';
import FileSection from '$lib/components/FileSection.svelte';
import type { DiffFile, LineAnchor } from '$lib/types';
import { lineAnchor } from '$lib/anchors/line';
import { contextLine, diffFile, diffResponse, hunk, removedLine, REVIEW_BASE, sinceRound } from './diff';
import { BAD_REQUEST, fakeServer, type FakeServer } from './fake-server';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const SINCE_ROUND_ONE = 'changes since round 1';
/** A request for the review's own diff, by the key the server named its base with. */
const WHOLE_REVIEW_ASKED = { method: 'GET', path: '/api/diff', query: { base: 'review' }, body: null };

/** A file whose only line, the first, the change left alone. */
function untouched(path: string): DiffFile {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** Lines of a.py a thread hangs on: line 1 on the new side, unless said otherwise. */
function lines(at: Partial<LineAnchor> = {}): LineAnchor {
	return { ...lineAnchor('a.py', 'new', 1, 1, []), ...at };
}

/** A server handing back these files, whatever base it was asked for. */
function serving(paths: string[], base = REVIEW_BASE): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/diff', diffResponse({ files: paths.map(untouched), base }));
	return server;
}

describe('what a round changed', () => {
	it('takes the tick off a file the round rewrote, and leaves the others alone', () => {
		review = openReview({
			files: [diffFile({ path: 'rewritten.py' }), diffFile({ path: 'untouched.py' })]
		});
		review.reading.setViewed('rewritten.py', true);
		review.reading.setViewed('untouched.py', true);

		review.noteRetake({ followed: 0, outdated: 0 }, { since_round: 2, base_key: 'round:2', paths: ['rewritten.py'] });

		expect(review.reading.isViewed('rewritten.py')).toBe(false);
		expect(review.reading.isViewed('untouched.py')).toBe(true);
		expect(review.lastRetake.isChanged('rewritten.py')).toBe(true);
		expect(review.lastRetake.changedSince).toBe(2);
	});

	it('brings a rewritten file back into view, or it sits folded and reads as read', () => {
		review = openReview({ files: [diffFile({ path: 'rewritten.py' })] });
		review.reading.setViewed('rewritten.py', true);

		review.noteRetake({ followed: 0, outdated: 0 }, { since_round: 2, base_key: 'round:2', paths: ['rewritten.py'] });

		expect(review.reading.isFolded('rewritten.py')).toBe(false);
	});

	it('trusts no tick when there is no way to tell what moved', () => {
		review = openReview({ files: [diffFile({ path: 'a.py' }), diffFile({ path: 'b.py' })] });
		review.reading.setViewed('a.py', true);
		review.reading.setViewed('b.py', true);

		review.noteRetake({ followed: 0, outdated: 0 }, null);

		expect(review.reading.viewedCount).toBe(0);
	});
});

describe('reading the same tree against something else', () => {
	it('asks for the diff against the base it was given', async () => {
		const server = serving(['answered.py'], sinceRound(1));

		await review.diff.setBase('round:1');

		expect(server.requests).toMatchObject([{ path: '/api/diff', query: { base: 'round:1' } }]);
		expect(review.diff.narrowed).toBe(true);
		expect(review.diff.phrase).toBe(SINCE_ROUND_ONE);
	});

	it('goes back to the whole review, and stops being narrowed', async () => {
		const server = serving(['answered.py'], sinceRound(1));
		await review.diff.setBase('round:1');

		server.answer('GET /api/diff', diffResponse({ files: [untouched('answered.py')] }));
		await review.diff.showWholeReview();

		// By naming no base: the server shows its own
		expect(server.requests.at(-1)).toEqual({ method: 'GET', path: '/api/diff', query: {}, body: null });
		expect(review.diff.narrowed).toBe(false);
		expect(review.diff.base).toBe(REVIEW_BASE.key);
	});

	it('stays where it was when the base cannot be taken', async () => {
		const server = fakeServer();
		server.refuse('GET /api/diff', BAD_REQUEST);

		await expect(review.diff.setBase('round:9')).rejects.toThrow();

		expect(review.diff.narrowed).toBe(false);
		server.answer('GET /api/diff', diffResponse({ files: [untouched('answered.py')] }));
		await review.diff.take();
		expect(server.requests.at(-1)).toEqual(WHOLE_REVIEW_ASKED);
	});

	it('keeps the base the reader picked when a round lands while it loads', async () => {
		const diffs = fakeServer().hold('GET /api/diff');
		const narrowed = diffResponse({ files: [untouched('answered.py')], base: sinceRound(1) });

		const picking = review.diff.setBase('round:1');
		const landing = review.diff.take();
		diffs.answer(1, narrowed);
		diffs.answer(0, narrowed);
		await Promise.all([picking, landing]);

		expect(diffs.requests[1]).toMatchObject({ path: '/api/diff', query: { base: 'round:1' } });
		expect(review.diff.base).toBe('round:1');
		expect(review.diff.narrowed).toBe(true);
	});
});

describe('a thread the base on screen cannot draw', () => {
	it('is not drawn when its file is not shown', () => {
		expect(isDrawn(lines({ file: 'elsewhere.py' }), [diffFile({ path: 'a.py' })])).toBe(false);
	});

	it('is not drawn when its lines are not among the ones shown', () => {
		expect(isDrawn(lines({ end_line: 40 }), [untouched('a.py')])).toBe(false);
	});

	it('is drawn when the row it hangs on is there', () => {
		expect(isDrawn(lines({ end_line: 1 }), [untouched('a.py')])).toBe(true);
	});

	it('leaves removed lines alone under a narrower base, whose left side is not ours', () => {
		const removed = lines({ side: 'old', end_line: 1 });
		const shown = [diffFile({ path: 'a.py', hunks: [hunk([removedLine(1, 'x')])] })];

		expect(isDrawn(removed, shown)).toBe(true);
		expect(isDrawn(removed, shown, { removedLines: false })).toBe(false);
	});
});

describe("a base that is not the review's own", () => {
	/** A file whose line 17 the change removed, with the line after it kept. */
	const answered = diffFile({
		path: 'answered.py',
		hunks: [hunk([removedLine(17, 'gone'), contextLine(18, 17, 'here')], { old_start: 17, new_start: 17 })]
	});

	/** The base on screen narrowed to a round, and this file drawn as Files draws it. */
	async function drawnUnderRoundOne() {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files: [answered], base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		return render(FileSection, inReview(review, { file: answered, scrollRoot: null }));
	}

	/** The numbers in the gutters of the row holding this text. */
	function guttersOf(text: string): HTMLElement[] {
		const row = screen.getByText(text).closest('tr');
		if (!row) throw new Error(`No row holds ${text}`);
		return within(row).getAllByRole('button');
	}

	it('refuses a thread on a removed line, whose numbering belongs to that base', async () => {
		const user = userEvent.setup();
		const { queryByTestId } = await drawnUnderRoundOne();

		for (const gutter of guttersOf('gone')) await user.click(gutter);

		expect(queryByTestId('comment-input')).toBeNull();
	});

	it('takes a thread on a line of the working tree, which every base shares', async () => {
		const user = userEvent.setup();
		const { getByTestId } = await drawnUnderRoundOne();

		await user.click(guttersOf('here')[0]);
		await user.type(getByTestId('comment-input'), 'still here');
		await user.click(getByTestId('save-comment'));

		expect(review.threads.all[0].anchor).toMatchObject({ side: 'new', start_line: 17 });
	});

	it('unfolds every file when there is no way to tell which ones moved', () => {
		review = openReview({ files: [diffFile({ path: 'a.py' }), diffFile({ path: 'b.py' })] });
		review.reading.setViewed('a.py', true);
		review.reading.setViewed('b.py', true);

		review.noteRetake({ followed: 0, outdated: 0 }, null);

		expect(review.reading.isFolded('a.py')).toBe(false);
		expect(review.reading.isFolded('b.py')).toBe(false);
		expect(review.lastRetake.changedKnown).toBe(false);
	});
});
