import { describe, it, expect, beforeEach } from 'vitest';
import { flushSync, tick } from 'svelte';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, diffResponse, hunk, REVIEW_BASE, sinceRound } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import { handOverNext } from '../pushes';
import { openReview } from '../review';
import { settled } from '../settled';

// Three files of one line each, a thread on each, in the order they were written
const PATHS = ['a.py', 'b.py', 'c.py'];
const files = PATHS.map((path) => diffFile({ path, hunks: [hunk([contextLine(1, 1, `in ${path}`)])] }));

let review: Review;
let ids: string[];

beforeEach(() => {
	review = openReview({ files, facts: { answerer_attached: true } });
	ids = PATHS.map((path) => review.threads.add(newComment({ file: path, body: `about ${path}` })));
});

/** The section a file is drawn in. */
function sectionOf(path: string): HTMLElement {
	const section = screen.getAllByTestId('file-section').find((candidate) => candidate.dataset.path === path);
	if (!section) throw new Error(`${path} is not drawn`);
	return section;
}

/** The thread drawn in a file's section, the one the keyboard lands on when the reader is taken to it. */
function threadIn(path: string): HTMLElement {
	return within(sectionOf(path)).getByTestId('comment-thread');
}

describe('every control that takes the reader to a thread', () => {
	it("steps through the threads by the header's arrows, the keyboard going with the reader", async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('next-comment'));
		expect(document.activeElement).toBe(threadIn('a.py'));

		await user.click(screen.getByTestId('next-comment'));
		expect(document.activeElement).toBe(threadIn('b.py'));

		await user.click(screen.getByTestId('prev-comment'));
		expect(document.activeElement).toBe(threadIn('a.py'));
	});

	it('steps back by p, from nowhere to the last thread, and on from there', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('p');
		expect(document.activeElement).toBe(threadIn('c.py'));

		await user.keyboard('p');
		expect(document.activeElement).toBe(threadIn('b.py'));
	});

	it('takes the reader to a reply picked from the list of replies, reads it, and n goes on from there', async () => {
		const user = userEvent.setup();
		review.threads.receiveReply(ids[1], 'Because.', null);
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('replies-menu'));
		await user.click(screen.getByTestId('reply-row'));
		await tick();

		expect(document.activeElement).toBe(threadIn('b.py'));
		expect(review.threads.unread).toEqual([]);
		await user.keyboard('n');
		expect(document.activeElement).toBe(threadIn('c.py'));
	});

	it('takes the reader to a thread the agent raised from its note in the panel', async () => {
		const user = userEvent.setup();
		const anchor = newComment({ file: 'b.py' }).anchor;
		handOverNext(review, { type: 'point', thread_id: 'raised-1', anchor, body: 'Look here', severity: 'note' });
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('panel-thread-ref'));

		const raised = within(sectionOf('b.py'))
			.getAllByTestId('comment-thread')
			.find((thread) => thread.textContent?.includes('Look here'));
		expect(raised).toBeDefined();
		expect(document.activeElement).toBe(raised);
	});

	it('takes the reader to the thread a retake left outdated, and n goes on from there', async () => {
		const user = userEvent.setup();
		review.threads.all[1].anchor.outdated = true;
		review.noteRetake({ followed: 0, outdated: 1 }, null);
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('show-outdated'));

		expect(document.activeElement).toBe(threadIn('b.py'));
		await user.keyboard('n');
		expect(document.activeElement).toBe(threadIn('c.py'));
	});

	it('takes the reader from a narrower base to a thread it cannot draw, on the whole diff', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		// The narrower base shows a.py alone; the review's own base shows all three
		server.answerWith('GET /api/diff', (request) =>
			request.query.base === 'round:1'
				? diffResponse({ files: files.slice(0, 1), base: sinceRound(1) })
				: diffResponse({ files, base: REVIEW_BASE })
		);
		await review.diff.setBase('round:1');
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('list-off-screen'));
		const [, toC] = screen.getAllByTestId('off-screen-thread');
		await user.click(toC);
		await settled();
		flushSync();

		expect(review.diff.files).toHaveLength(PATHS.length);
		expect(document.activeElement).toBe(threadIn('c.py'));
	});
});
