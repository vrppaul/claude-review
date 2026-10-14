import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { StoryAsking } from '$lib/types';
import { addedLine, diffFile, hunk } from '../diff';
import { said } from '../elements';
import { takingStoryAskings } from '../fake-server';
import { handOverNext } from '../pushes';
import { openReview, type Opened } from '../review';
import { STOPPED } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one')])] })];

const SECOND = 1000;
// Ten seconds past four minutes past one in the afternoon, wherever the tests are run: when the reader
// asked for a story. An agent took the request two seconds later
const ASKED_AT = new Date(2026, 9, 14, 13, 4, 10).getTime();
const TAKEN_AT = ASKED_AT + 2 * SECOND;
const ASKED: StoryAsking = { asked_at: ASKED_AT, taken_at: null, stopped: false };
const TAKEN: StoryAsking = { asked_at: ASKED_AT, taken_at: TAKEN_AT, stopped: false };
// What the review says of itself with an agent attached
const AGENT_ATTACHED = { answerer_attached: true };

/** Draw a review that holds no story, read as its story: what the reader waits on is all there is to draw. */
function waiting(opened: Opened): Review {
	const review = openReview({ files, ...opened });
	review.views.choose('story');
	render(ReviewScreen, { props: { review } });
	return review;
}

/** What is said where the story will be, of what the reader waits on. */
function saidOfTheWait(): string {
	return said(screen.getByTestId('story-waiting'));
}

/** What each fact listed of the story being written says, in the order they are listed. */
function facts(): string[] {
	return screen.getAllByTestId('story-wait-fact').map(said);
}

describe('a story being written, its request taken by an agent', () => {
	it('says the agent is writing it, and how long a big change takes', () => {
		waiting({ asking: TAKEN });

		expect(saidOfTheWait()).toContain('The agent is writing the story');
		expect(saidOfTheWait()).toContain(
			'It reads the whole change and writes the overview and the chapters in one go. A big change takes a few minutes.'
		);
	});

	it('lists when it was asked for and when the agent took the request, each to the second', () => {
		waiting({ asking: TAKEN });

		expect(facts()).toEqual([
			expect.stringMatching(/Asked the agent for a story.*:04:10/),
			expect.stringMatching(/The agent took the request.*:04:12/),
			expect.stringContaining('Waiting for the story')
		]);
	});

	it('counts how long the story has been waited for since the agent took the request, second by second', async () => {
		vi.useFakeTimers();
		vi.setSystemTime(TAKEN_AT + 48 * SECOND);
		waiting({ asking: TAKEN });

		expect(facts().at(-1)).toMatch(/Waiting for the story.*0:48/);
		await vi.advanceTimersByTimeAsync(SECOND);
		flushSync();

		expect(facts().at(-1)).toMatch(/Waiting for the story.*0:49/);
	});

	it('stops the story where the reader says so', async () => {
		const server = takingStoryAskings();
		const user = userEvent.setup();
		waiting({ asking: TAKEN });

		await user.click(screen.getByTestId('stop-writing'));

		expect(server.requestsTo('POST /api/story/cancel')).toHaveLength(1);
	});

	it('brings the files on screen meanwhile, and leaves the story as how the reader chose to read', async () => {
		const user = userEvent.setup();
		const review = waiting({ asking: TAKEN });

		await user.click(screen.getByTestId('read-files-meanwhile'));

		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(review.layout.readingView.name).toBe('story');
	});
});

describe('a story asked for, its request not yet taken by the agent attached', () => {
	it('lists when it was asked for, and counts how long the agent has not taken the request', async () => {
		vi.useFakeTimers();
		vi.setSystemTime(ASKED_AT + 5 * SECOND);
		waiting({ asking: ASKED, facts: AGENT_ATTACHED });

		expect(facts()).toEqual([
			expect.stringMatching(/Asked the agent for a story.*:04:10/),
			expect.stringMatching(/Waiting for the agent to take the request.*0:05/)
		]);
		await vi.advanceTimersByTimeAsync(SECOND);
		flushSync();

		expect(facts().at(-1)).toMatch(/Waiting for the agent to take the request.*0:06/);
	});

	it('can be stopped', () => {
		waiting({ asking: ASKED, facts: AGENT_ATTACHED });

		expect(said(screen.getByTestId('stop-writing'))).toBe('Stop writing');
	});
});

describe('a story whose request has not landed yet', () => {
	it('says the agent is being asked', () => {
		waiting({ asking: null });

		expect(saidOfTheWait()).toContain('The agent is writing the story');
		expect(facts()).toEqual(['Asking the agent for a story']);
	});

	it('offers the files meanwhile, and nothing to stop: nothing is asked yet', () => {
		waiting({ asking: null });

		expect(said(screen.getByTestId('read-files-meanwhile'))).toBe('Read the files meanwhile');
		expect(screen.queryByTestId('stop-writing')).toBeNull();
	});
});

describe('a story asked for with no agent attached', () => {
	it('says no story is told without the agent, and how one is attached', () => {
		waiting({ asking: ASKED });

		expect(saidOfTheWait()).toContain(
			'No story for this review. A story is told by the agent that made the change, and no agent is attached.'
		);
		expect(saidOfTheWait()).toContain(
			'Attach one with /review-ui in that session; the story starts as soon as it joins.'
		);
	});

	it('offers nothing that cannot work: its one button waits for an agent, and takes no press', () => {
		waiting({ asking: ASKED });

		const button = screen.getByTestId<HTMLButtonElement>('waiting-for-an-agent');
		expect(said(button)).toBe('Waiting for an agent');
		expect(button.disabled).toBe(true);
		expect(screen.queryByTestId('stop-writing')).toBeNull();
	});
});

describe('a story the reader stopped', () => {
	it('says it was not finished, and that the files are there to read', () => {
		waiting({ asking: STOPPED });

		expect(saidOfTheWait()).toContain('The story was not finished: you stopped it.');
		expect(saidOfTheWait()).toContain('or read the files');
	});

	it('is asked for again where the reader says so', async () => {
		const server = takingStoryAskings();
		const user = userEvent.setup();
		waiting({ asking: STOPPED });

		await user.click(screen.getByTestId('write-story-again'));

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('is said to be stopped as soon as the review says so', () => {
		const review = waiting({ asking: TAKEN });

		handOverNext(review, { type: 'story_asking', asking: { ...TAKEN, stopped: true } });
		flushSync();

		expect(saidOfTheWait()).toContain('The story was not finished: you stopped it.');
		expect(screen.queryByTestId('stop-writing')).toBeNull();
	});
});

describe('what the reader waits on', () => {
	it('is said to whoever cannot see it, as it changes', () => {
		waiting({ asking: TAKEN });

		expect(screen.getByTestId('story-waiting').getAttribute('role')).toBe('status');
	});
});
