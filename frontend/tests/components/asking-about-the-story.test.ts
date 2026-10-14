import { beforeEach, describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { AGENT_ATTACHED, openReview } from '../review';
import { storyHeld, toldStory } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one')])] })];
// What the overview says: the task, what was done, and what to doubt
const TASK = 'Let the reader paste a screenshot.';
const DONE = 'A pasted image goes to the review.';
const DOUBT = 'Whether an image is checked before it is kept.';
const TOLD = storyHeld({ overview: { ...toldStory().overview, task: TASK, done: DONE, doubt: DOUBT } });

let review: Review;

/** Ask about a block of the overview, by its test id, and write a comment on it. */
async function writeAbout(block: string, comment: string): Promise<ReturnType<typeof userEvent.setup>> {
	const user = userEvent.setup();
	await user.click(within(screen.getByTestId(block)).getByTestId('ask-about-this'));
	await user.type(screen.getByTestId('comment-input'), comment);
	return user;
}

describe("the overview's three lines", () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD, facts: AGENT_ATTACHED });
		review.views.choose('story');
	});

	it('each offer to be asked about', () => {
		render(ReviewScreen, { props: { review } });

		for (const block of ['overview-task', 'overview-done', 'overview-doubt']) {
			expect(within(screen.getByTestId(block)).getByTestId('ask-about-this').textContent).toContain('Ask about this');
		}
	});

	it('open a comment under the block asked about, headed by what the story heads it with, which may ask straight away', async () => {
		render(ReviewScreen, { props: { review } });

		await userEvent.setup().click(within(screen.getByTestId('overview-doubt')).getByTestId('ask-about-this'));

		const field = within(screen.getByTestId('overview-doubt')).getByTestId('comment-box');
		expect(within(field).getByText('Doubt')).toBeTruthy();
		expect(within(field).getByTestId('ask-now')).toBeTruthy();
	});

	it('take a comment as a thread on the words of the block, drawn under it alone and named as the story heads it', async () => {
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-doubt', 'Is it checked at all?');
		await user.click(screen.getByTestId('save-comment'));

		expect(review.threads.all.map((thread) => thread.anchor)).toEqual([
			{ kind: 'story', block: { at: 'overview', text: 'doubt' }, quote: [DOUBT], outdated: false }
		]);
		const drawn = within(screen.getByTestId('overview-doubt')).getByTestId('comment-thread');
		expect(drawn.getAttribute('aria-label')).toBe('Thread on Story · Doubt');
		expect(within(screen.getByTestId('overview-task')).queryByTestId('comment-thread')).toBeNull();
	});

	it('hand a question on a block straight to the agent, with the words it is on', async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', null);
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-task', 'Why only a screenshot?');
		await user.click(screen.getByTestId('ask-now'));

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { anchor: { kind: 'story', block: { at: 'overview', text: 'task' }, quote: [TASK] } } }
		]);
	});

	it('put a comment away unsaid, and leave the block as it was', async () => {
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-done', 'Not this one.');
		await user.click(screen.getByTestId('cancel-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));

		expect(screen.queryByTestId('comment-box')).toBeNull();
		expect(review.threads.all).toEqual([]);
	});
});
