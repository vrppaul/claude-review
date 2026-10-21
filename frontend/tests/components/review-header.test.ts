import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushSync, tick } from 'svelte';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { lineAnchor } from '$lib/anchors/line';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { ReviewResponse } from '$lib/types';
import { contextLine, diffFile, hunk } from '../diff';
import { fakeServer, SERVER_ERROR } from '../fake-server';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

const file = diffFile({ path: 'test.py', hunks: [hunk([contextLine(1, 1, 'hello')])] });
// Where the author raises a thread: the file's one line
const RAISED_ON = lineAnchor('test.py', 'new', 1, 1, ['hello']);
// A review of files compared against nothing: the header names it rather
// than offering bases
const READ_WHOLE = { base: null };

describe('sending the review', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview({ files: [file], diff: READ_WHOLE });
	});

	it("names on Send how many comments go with it, apart from the round's number, and never the author's", () => {
		// A round sent to an agent there, and the end of a review with none, each a review of its own, which keeps a
		// draft of its own; how many comments each holds, how many of them went in a round before, how many threads
		// the author raised, and what Send is called. A round takes the reader's unsent; the end takes everything
		const sends = [
			{
				review: 'a-round',
				attached: true,
				comments: 2,
				sentBefore: 1,
				raised: 0,
				named: 'Send round 1 (1 comment goes with it)'
			},
			{
				review: 'the-end',
				attached: false,
				comments: 2,
				sentBefore: 1,
				raised: 0,
				named: 'Finish review (2 comments go with it)'
			},
			{ review: 'a-raised-thread', attached: true, comments: 0, sentBefore: 0, raised: 1, named: 'Send round 1' },
			{ review: 'nothing-written', attached: false, comments: 0, sentBefore: 0, raised: 0, named: 'Finish review' }
		];

		const namedSo = sends.map(({ review: identity, attached, comments, sentBefore, raised, named }) => {
			const sending = openReview({
				files: [file],
				diff: READ_WHOLE,
				facts: { identity, answerer_attached: attached }
			});
			Array.from({ length: comments }, (_, index) =>
				sending.threads.add(newComment({ file: 'test.py', startLine: index + 1, body: 'fix' }))
			);
			Array.from({ length: raised }, (_, index) =>
				sending.threads.raise(`raised-${index + 1}`, RAISED_ON, 'Kept on purpose', 'note')
			);
			sending.threads.markSent(sending.threads.carry(sending.threads.all.slice(0, sentBefore)), 1);
			const sent = within(render(ReviewHeader, inReview(sending)).container);
			return sent.queryByRole('button', { name: named }) === sent.getByTestId('quick-submit');
		});

		expect(namedSo).toEqual(sends.map(() => true));
	});

	it('can be opened once something is written', () => {
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});

	it('opens even with nothing written, because a summary alone is a review', () => {
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect((getByTestId('quick-submit') as HTMLButtonElement).disabled).toBe(false);
	});
});

describe('a review that is over', () => {
	it('says it was sent, wherever it was sent from', () => {
		const review = openReview({ files: [file] });

		review.link.end('finished');
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('submitted-banner').textContent).toContain('Review sent');
		expect(queryByTestId('top-bar')).toBeNull();
	});

	it('says one stopped under the reader keeps what was not sent', () => {
		const review = openReview({ files: [file] });

		review.link.end('stopped');
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('review-stopped').textContent).toContain('What you had not sent is kept');
	});

	it('says another review answers here now, and that what was not sent is kept', () => {
		const review = openReview({ files: [file] });

		review.link.end('replaced');
		const { getByTestId } = render(ReviewHeader, inReview(review));

		expect(getByTestId('review-replaced').textContent).toContain('another review is running here now');
		expect(getByTestId('review-replaced').textContent).toContain('What you had not sent is kept');
	});
});

describe('a review that cannot be reached', () => {
	it('says so, and that nothing is sent until it is back', () => {
		const review = openReview({ files: [file] });
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));
		expect(queryByTestId('connection-lost')).toBeNull();

		review.link.lost();
		flushSync();

		expect(getByTestId('connection-lost').textContent).toContain('Nothing is sent until it is back');
		review.link.reached();
		flushSync();
		expect(queryByTestId('connection-lost')).toBeNull();
	});

	it('holds the send back in the pane, and the end with it', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file], facts: { answerer_attached: true } });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		render(ReviewScreen, { props: { review } });
		await user.click(screen.getByTestId('quick-submit'));

		review.link.lost();
		flushSync();

		expect((screen.getByTestId('modal-submit') as HTMLButtonElement).disabled).toBe(true);
		expect((screen.getByTestId('end-review') as HTMLButtonElement).disabled).toBe(true);
	});
});

describe('the review header', () => {
	it('says where the change is: the repository over its branch or its commit, else what is reviewed', () => {
		// Each kind of review, and the lines its header says where the change is in
		const reviews: { facts: Partial<ReviewResponse>; lines: string[] }[] = [
			{
				facts: { mode: 'diff', repository: { name: 'shop', checkout: { at: 'branch', branch: 'feature/cart' } } },
				lines: ['shop', 'feature/cart']
			},
			{
				facts: { mode: 'diff', repository: { name: 'shop', checkout: { at: 'commit', commit: 'a1b2c3d' } } },
				lines: ['shop', 'a1b2c3d']
			},
			{ facts: { mode: 'files', repository: null, title: 'plan.md, notes.md' }, lines: ['plan.md, notes.md'] },
			{
				facts: { mode: 'transcript', repository: null, title: 'Conversation 63b8ade4' },
				lines: ['Conversation 63b8ade4']
			}
		];

		const said = reviews.map(({ facts }) => {
			const { container } = render(ReviewHeader, inReview(openReview({ files: [file], facts, diff: READ_WHOLE })));
			return within(container)
				.getAllByTestId('where-line')
				.map((line) => line.textContent?.trim());
		});

		expect(said).toEqual(reviews.map(({ lines }) => lines));
	});

	it('offers comment navigation only once there is a comment', async () => {
		const review = openReview({ files: [file], diff: READ_WHOLE });

		const { queryByTestId, rerender } = render(ReviewHeader, inReview(review));
		expect(queryByTestId('next-comment')).toBeNull();

		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		await rerender({});

		expect(queryByTestId('next-comment')).toBeTruthy();
	});

	it('opens one door to everything that ends a round', async () => {
		const user = userEvent.setup({ delay: null });
		const review = openReview({ files: [file], diff: READ_WHOLE });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));

		const { getByTestId } = render(ReviewHeader, inReview(review));
		await user.click(getByTestId('quick-submit'));

		// What was written, a summary, and the two ways out — all in one place
		expect(getByTestId('finish-review')).toBeTruthy();
		expect(getByTestId('finish-comment')).toBeTruthy();
		expect(getByTestId('review-body')).toBeTruthy();
		expect(getByTestId('modal-submit')).toBeTruthy();
	});
});

describe('the pane the review is sent from', () => {
	// What the server says to a round, and to a review sent for good
	const ROUND_SENT = { markdown: '## Round', comment_count: 1, round: 1, ended: false };
	const SENT_FOR_GOOD = { markdown: '## Review', comment_count: 1, round: 1, ended: true };

	/** The whole review on screen, as the page draws it. */
	function onScreen(review: Review) {
		return render(ReviewScreen, { props: { review } });
	}

	/** The number of a line, to press it by. */
	function lineNumber(number: number): HTMLElement {
		const gutter = screen
			.getAllByTestId('line-gutter')
			.find((candidate) => candidate.textContent?.trim() === String(number));
		if (!gutter) throw new Error(`Line ${number} is not drawn`);
		return gutter;
	}

	it('gives way to a press anywhere else, and the press does what it was for', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));

		await user.click(lineNumber(1));

		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(screen.getByTestId('comment-input')).toBeTruthy();
	});

	it('goes on Escape, hands the keyboard back to the button that opened it, and keeps the summary written in it', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));
		expect(document.activeElement).toBe(screen.getByTestId('review-body'));
		await user.type(screen.getByTestId('review-body'), 'Draft feedback');

		await user.keyboard('{Escape}');

		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('quick-submit'));
		await user.click(screen.getByTestId('quick-submit'));
		expect((screen.getByTestId('review-body') as HTMLTextAreaElement).value).toBe('Draft feedback');
	});

	it('takes the reader, keyboard and all, to the thread a row of the pane names, though a field opened it', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(lineNumber(1));
		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');

		await user.click(screen.getByTestId('finish-comment'));
		await tick();

		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('comment-thread'));
	});

	it('gives the keyboard back to the field it was opened from without moving the screen', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [file] });
		onScreen(review);
		await user.click(lineNumber(1));
		const handedBack = vi.spyOn(screen.getByTestId('comment-input'), 'focus');
		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');

		await user.keyboard('{Escape}');
		await tick();

		expect(handedBack.mock.calls).toEqual([[{ preventScroll: true }]]);
	});

	it('opens from the keys while a comment is being written, and sends with them once open', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('POST /api/submit', SENT_FOR_GOOD);
		const review = openReview({ files: [file] });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(lineNumber(1));

		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');
		expect(screen.getByTestId('finish-review')).toBeTruthy();
		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');

		expect(server.requestsTo('POST /api/submit')).toHaveLength(1);
	});

	it('says why a send did not go, and stays open with everything in it', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.fail('POST /api/submit', SERVER_ERROR);
		const review = openReview({ files: [file], facts: { answerer_attached: true } });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));
		await user.type(screen.getByTestId('review-body'), 'mostly fine');

		await user.click(screen.getByTestId('modal-submit'));

		expect(screen.getByTestId('submit-error').textContent).toContain(SERVER_ERROR);
		expect((screen.getByTestId('review-body') as HTMLTextAreaElement).value).toBe('mostly fine');
		server.answer('POST /api/submit', ROUND_SENT);
		await user.click(screen.getByTestId('modal-submit'));
		expect(screen.queryByTestId('finish-review')).toBeNull();
		expect(screen.queryByTestId('submit-error')).toBeNull();
	});

	it("says in words that a send never reached the review, not in the browser's", async () => {
		const user = userEvent.setup();
		fakeServer().drop('POST /api/submit');
		const review = openReview({ files: [file], facts: { answerer_attached: true } });
		review.threads.add(newComment({ file: 'test.py', body: 'fix' }));
		onScreen(review);
		await user.click(screen.getByTestId('quick-submit'));

		await user.click(screen.getByTestId('modal-submit'));

		expect(screen.getByTestId('submit-error').textContent).toBe('Could not send the review: the review did not answer');
	});
});
