import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import DiffView from '$lib/components/DiffView.svelte';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import { contextLine, diffFile, diffResponse, hunk } from '../diff';
import { said } from '../elements';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

const A_MINUTE_AND_A_BIT = 61_000;
const TWELVE_SECONDS = 12_000;
const FORTY_SECONDS = 40_000;
const TWO_MINUTES = 120_000;

const file = diffFile({
	path: 'a.py',
	hunks: [hunk([contextLine(1, 1, 'one'), contextLine(2, 2, 'two'), contextLine(3, 3, 'three')])]
});

afterEach(() => {
	vi.useRealTimers();
});

/** A review with a question on each of these lines, every one still with the agent. */
function waitingOn(lines: number[]) {
	const review = openReview({ files: [file], facts: { answerer_attached: true } });
	for (const line of lines) {
		const id = review.threads.add(newComment({ file: 'a.py', startLine: line, body: `why ${line}` }));
		review.threads.reading.asked(id, id);
	}
	return review;
}

describe('how long a question has waited', () => {
	it('is said in minutes once it is past one, not in a count of seconds', async () => {
		vi.useFakeTimers();
		const review = waitingOn([1]);
		render(DiffView, inReview(review));

		await vi.advanceTimersByTimeAsync(A_MINUTE_AND_A_BIT);
		flushSync();

		expect(screen.getByTestId('awaiting-answer').textContent).toContain('asked 1m ago');
	});
});

describe('who said each turn of a thread, and how long ago', () => {
	it('says the reader asked two minutes ago and the agent answered forty seconds ago', async () => {
		vi.useFakeTimers();
		const review = openReview({ files: [file] });
		const id = review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'why' }));
		await vi.advanceTimersByTimeAsync(TWO_MINUTES - FORTY_SECONDS);
		review.threads.receiveReply(id, 'because', id);
		render(DiffView, inReview(review));

		await vi.advanceTimersByTimeAsync(FORTY_SECONDS);
		flushSync();

		expect(said(screen.getByTestId('thread-question'))).toMatch(/^You 2m ago/);
		expect(said(screen.getByTestId('thread-answer'))).toMatch(/^Agent answered 40s ago/);
	});

	it('names the reader on a comment nobody has answered yet', () => {
		const review = openReview({ files: [file] });
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'why' }));

		render(DiffView, inReview(review));

		expect(said(screen.getByTestId('thread-question'))).toMatch(/^You /);
	});
});

describe('how old a base is', () => {
	it('is said in seconds when it was taken a moment ago', async () => {
		// The time stands still, so the list says what it says however long the test takes to draw it
		vi.useFakeTimers({ toFake: ['Date'] });
		const taken = Date.now() - TWELVE_SECONDS;
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse());
		server.answer('GET /api/versions', {
			versions: [
				{ key: 'round:1', kind: 'round', label: 'Round 1', phrase: 'changes since round 1', at: taken, changed: null }
			]
		});
		const review = openReview({ files: [file] });
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));

		await user.click(screen.getByTestId('base-picker'));

		expect(await screen.findByText('12s ago')).toBeTruthy();
	});
});
