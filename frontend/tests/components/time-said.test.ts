import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import DiffView from '$lib/components/DiffView.svelte';
import TopBar from '$lib/components/TopBar.svelte';
import { contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

const A_MINUTE_AND_A_BIT = 61_000;
const TWELVE_SECONDS = 12_000;
// Longer than the draft waits before it keeps what changed: the timers left after it are the clock's
const THE_DRAFT_KEPT = 1_000;
const HEADER = { submitting: false, error: null, onOpenModal: () => undefined };

const file = diffFile({
	path: 'a.py',
	hunks: [hunk([contextLine(1, 1, 'one'), contextLine(2, 2, 'two'), contextLine(3, 3, 'three')])]
});

afterEach(() => {
	vi.useRealTimers();
});

/** A review with a question on each of these lines, every one still with the agent. */
function waitingOn(lines: number[]) {
	const review = openReview({ files: [file] });
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

	it('keeps one clock however many questions wait', async () => {
		vi.useFakeTimers();
		const review = waitingOn([1, 2, 3]);
		render(DiffView, inReview(review));
		await vi.advanceTimersByTimeAsync(THE_DRAFT_KEPT);

		expect(screen.getAllByTestId('awaiting-answer')).toHaveLength(3);
		expect(vi.getTimerCount()).toBe(1);
	});

	it('keeps no clock once nothing is waited on', async () => {
		vi.useFakeTimers();
		const review = waitingOn([1]);
		render(DiffView, inReview(review));
		flushSync();

		const [thread] = review.threads.all;
		review.threads.receiveReply(thread.id, 'because', thread.id);
		await vi.advanceTimersByTimeAsync(THE_DRAFT_KEPT);

		expect(vi.getTimerCount()).toBe(0);
	});
});

describe('how old a base is', () => {
	it('is said in seconds when it was taken a moment ago', async () => {
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
		render(TopBar, inReview(review, HEADER));

		await user.click(screen.getByTestId('base-picker'));

		expect(await screen.findByText('12s ago')).toBeTruthy();
	});
});
