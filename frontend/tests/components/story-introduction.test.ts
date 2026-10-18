import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { said } from '../elements';
import { keepingSettings, takingStoryAskings, type FakeServer } from '../fake-server';
import { guideServer } from '../guide-server';
import { handOverNext } from '../pushes';
import { openReview, settingsWithStoriesOn, type Opened } from '../review';
import { settled } from '../settled';
import { storyHeld, storyResponse, TAKEN, toldChapter, toldStep } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one')])] })];
// The release serving the review, which the reader was shown already: no card of the guide's stands
const RELEASE = '1.5.0';
// How long the notice that Story is put away for good stands: four seconds, as every note that goes by itself
const NOTICE_STANDS_FOR = 4_000;
const A_SECOND = 1_000;
// A story of the change, told already, for a reader who reads the review as its story
const A_STORY = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('a.py', 1)])] });

/** A server that keeps how far the reader was shown around and their choices, and takes every story asked for. */
function serving(): FakeServer {
	const server = guideServer(RELEASE);
	takingStoryAskings(server);
	keepingSettings(server);
	return server;
}

/** Draw a review for a reader Story was never introduced to, once the guide has heard so. */
async function drawn(opened: Opened = {}): Promise<Review> {
	const review = openReview({ files, facts: { release: RELEASE }, ...opened });
	await review.guide.open();
	render(ReviewScreen, { props: { review } });
	flushSync();
	return review;
}

/** Say "Don't show again" to the introduction. */
async function hiddenForGood(user: ReturnType<typeof userEvent.setup>): Promise<void> {
	await user.click(screen.getByTestId('story-introduction-hide'));
}

describe('Story introduced at the switch', () => {
	it('says what a story is and what it spends, and offers to try it', async () => {
		serving();
		await drawn();

		const introduction = said(screen.getByTestId('story-introduction'));
		expect(introduction).toContain('Read the change as a story');
		expect(introduction).toContain(
			'The agent that made it walks you through: a short overview, then chapters, with its reason above each piece of code. Your threads and rounds work the same.'
		);
		expect(introduction).toContain("It spends the agent's tokens, so it asks before it starts.");
		expect(said(screen.getByTestId('try-story'))).toBe('Try Story');
		expect(said(screen.getByTestId('story-introduction-hide'))).toBe("Don't show again");
	});

	it('is named for whoever cannot see it, and its cross says it closes it for now', async () => {
		serving();
		await drawn();

		expect(screen.getByTestId('story-introduction').getAttribute('aria-label')).toBe('Read the change as a story');
		expect(screen.getByTestId('story-introduction-close').getAttribute('aria-label')).toBe('Close for now');
	});

	it('shows a story, sketched', async () => {
		serving();
		await drawn();

		expect(within(screen.getByTestId('story-introduction')).getByTestId('story-sketch')).toBeTruthy();
	});

	it('asks before stories are turned on, where Try Story is pressed with stories off', async () => {
		serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('try-story'));

		expect(screen.getByTestId('story-opt-in')).toBeTruthy();
		expect(screen.queryByTestId('story-introduction')).toBeNull();
	});

	it('shows the story view where Try Story is pressed with stories on', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn({ settings: await settingsWithStoriesOn(server), asking: TAKEN });

		await user.click(screen.getByTestId('try-story'));

		expect(screen.getByTestId('story-view')).toBeTruthy();
	});

	it('keeps that Story was introduced, once Try Story is pressed', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('try-story'));

		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});

	it('is put away for this review by its cross, and nothing is kept', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('story-introduction-close'));
		await settled();

		expect(screen.queryByTestId('story-introduction')).toBeNull();
		expect(server.bodiesSentTo('PUT /api/guide')).toEqual([]);
	});

	it('keeps that Story was introduced where the reader says not to show it again', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();

		await hiddenForGood(user);

		expect(screen.queryByTestId('story-introduction')).toBeNull();
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});

	it('says in its place that it is gone for good, and where Story still is', async () => {
		serving();
		const user = userEvent.setup();
		await drawn();

		await hiddenForGood(user);

		expect(said(screen.getByTestId('story-introduction-hidden'))).toBe(
			"Won't show again, in any review. Story is still in the header. Undo"
		);
		expect(screen.getByTestId('story-introduction-hidden').getAttribute('role')).toBe('status');
	});

	it('comes back by Undo, and Story is kept as not introduced', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();
		await hiddenForGood(user);

		await user.click(screen.getByTestId('story-introduction-undo'));

		expect(screen.getByTestId('story-introduction')).toBeTruthy();
		expect(screen.queryByTestId('story-introduction-hidden')).toBeNull();
		await vi.waitFor(() =>
			expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }, { story_introduced: false }])
		);
	});

	it('leaves nothing in its place where it is put away for now after Undo', async () => {
		serving();
		const user = userEvent.setup();
		await drawn();
		await hiddenForGood(user);
		await user.click(screen.getByTestId('story-introduction-undo'));

		await user.click(screen.getByTestId('story-introduction-close'));

		expect(screen.queryByTestId('story-introduction')).toBeNull();
		expect(screen.queryByTestId('story-introduction-hidden')).toBeNull();
	});

	it('says it is gone for good until its four seconds are out', async () => {
		vi.useFakeTimers({ shouldAdvanceTime: true });
		serving();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime.bind(vi) });
		await drawn();
		await hiddenForGood(user);

		vi.advanceTimersByTime(NOTICE_STANDS_FOR - A_SECOND);
		flushSync();

		expect(screen.getByTestId('story-introduction-hidden')).toBeTruthy();
	});

	it('stops saying it is gone for good once its four seconds are out, and does not come back', async () => {
		vi.useFakeTimers({ shouldAdvanceTime: true });
		serving();
		const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime.bind(vi) });
		await drawn();
		await hiddenForGood(user);

		vi.advanceTimersByTime(NOTICE_STANDS_FOR);
		flushSync();

		expect(screen.queryByTestId('story-introduction-hidden')).toBeNull();
		expect(screen.queryByTestId('story-introduction')).toBeNull();
	});

	it('stands nowhere while the reader reads the story: they are trying it', async () => {
		openReview({ files, story: A_STORY }).views.choose('story');
		serving();

		await drawn({ story: A_STORY });

		expect(screen.queryByTestId('story-introduction')).toBeNull();
	});

	it('is kept as done once the reader reads the story, as Try Story keeps it', async () => {
		openReview({ files, story: A_STORY }).views.choose('story');
		const server = serving();

		await drawn({ story: A_STORY });

		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});

	it('waits while the note of a story that arrived stands under the switch', async () => {
		const server = serving();
		const review = await drawn({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		server.answer('GET /api/story', storyResponse({ held: A_STORY }));

		handOverNext(review, { type: 'story' });
		await settled();

		expect(screen.getByTestId('story-ready')).toBeTruthy();
		expect(screen.queryByTestId('story-introduction')).toBeNull();
	});

	it('rings Story while it introduces it, and not while the note of a story that arrived stands in its place', async () => {
		const server = serving();
		const review = await drawn({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		server.answer('GET /api/story', storyResponse({ held: A_STORY }));
		const calling = () => screen.getByTestId('read-as-story').getAttribute('data-calling');
		const whileIntroduced = calling();

		handOverNext(review, { type: 'story' });
		await settled();

		expect([whileIntroduced, calling()]).toEqual(['introduced', 'unread']);
	});

	it('hands the keyboard it held to Story where the note of a story that arrived takes its place', async () => {
		const server = serving();
		const review = await drawn({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		server.answer('GET /api/story', storyResponse({ held: A_STORY }));
		screen.getByTestId('try-story').focus();

		handOverNext(review, { type: 'story' });
		await settled();

		expect(document.activeElement).toBe(screen.getByTestId('read-as-story'));
	});

	it('is kept as done once a thread only the story draws brings the story on screen', async () => {
		const server = serving();
		const review = await drawn({ story: A_STORY });

		review.wayIntoStory.showStory();

		expect(review.guide.introducesStory).toBe(false);
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ story_introduced: true }]));
	});
});
