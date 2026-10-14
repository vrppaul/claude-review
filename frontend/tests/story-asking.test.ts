import { describe, it, expect } from 'vitest';
import { fakeServer, keepingSettings, SERVER_ERROR, takingStoryAskings, type FakeServer } from './fake-server';
import { handOverNext } from './pushes';
import { openReview, settingsWithStoriesOn } from './review';
import { ASKED, STOPPED, storyHeld, TAKEN } from './story';

/** A server that keeps the reader's choices, and takes every story asked for or stopped. */
function serving(): FakeServer {
	const server = takingStoryAskings();
	keepingSettings(server);
	return server;
}

describe('turning stories on', () => {
	it('keeps the choice for every later review', async () => {
		const server = serving();
		const review = openReview();

		await review.turnStoriesOn();

		expect(review.settings.current.stories).toBe(true);
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ stories: true }]);
	});

	it('asks the agent for a story of the review on screen', async () => {
		const server = serving();
		const review = openReview();

		await review.turnStoriesOn();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it.each([
		{ where: 'the review holds a story', opened: { story: storyHeld() } },
		{ where: 'one is being written already', opened: { asking: TAKEN } },
		{ where: 'one asked for waits for an agent to attach', opened: { asking: ASKED } },
		{ where: 'no story can be told of the review', opened: { facts: { takes_a_story: false } } }
	])('asks for no story where $where', async ({ opened }) => {
		const server = serving();
		const review = openReview(opened);

		await review.turnStoriesOn();

		expect(server.requestsTo('POST /api/story/request')).toEqual([]);
	});

	it('asks for a story the reader stopped: turned on, stories are wanted again', async () => {
		const server = serving();
		const review = openReview({ asking: STOPPED });

		await review.turnStoriesOn();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('asks again for the story that turning stories off stopped', async () => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		await review.turnStoriesOff();
		handOverNext(review, { type: 'story_asking', asking: { ...TAKEN, stopped: true } });

		await review.turnStoriesOn();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('says in the panel why a story could not be asked for', async () => {
		const server = serving();
		server.refuse('POST /api/story/request', SERVER_ERROR, 'the review fell over');
		const review = openReview();

		await review.turnStoriesOn();

		expect(review.conversation.turns.at(-1)?.body).toBe('the story could not be asked for — the review fell over');
	});
});

describe('turning stories off', () => {
	it('keeps the choice for every later review', async () => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server) });

		await review.turnStoriesOff();

		expect(review.settings.current.stories).toBe(false);
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ stories: false }]);
	});

	it.each([
		{ awaited: 'one an agent is writing', asking: TAKEN },
		{ awaited: 'one that waits for an agent to attach', asking: ASKED }
	])('stops the story awaited: $awaited', async ({ asking }) => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), asking });

		await review.turnStoriesOff();

		expect(server.requestsTo('POST /api/story/cancel')).toHaveLength(1);
	});

	it.each([
		{ where: 'none was asked for', opened: {} },
		{ where: 'the reader stopped it already', opened: { asking: STOPPED } },
		{ where: 'the story is held', opened: { story: storyHeld() } }
	])('stops nothing where $where', async ({ opened }) => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), ...opened });

		await review.turnStoriesOff();

		expect(server.requestsTo('POST /api/story/cancel')).toEqual([]);
	});

	it('brings the files on screen where the story view has no story to draw', async () => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		review.views.choose('story');

		await review.turnStoriesOff();

		expect(review.views.onScreen.name).toBe('files');
	});

	it('leaves a story the review holds on screen: it is paid for, and still read', async () => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), story: storyHeld() });
		review.views.choose('story');

		await review.turnStoriesOff();

		expect(review.views.onScreen.name).toBe('story');
	});

	it('says in the panel why the story could not be stopped', async () => {
		const server = fakeServer();
		keepingSettings(server);
		server.refuse('POST /api/story/cancel', SERVER_ERROR, 'the review fell over');
		const review = openReview({ settings: await settingsWithStoriesOn(server), asking: TAKEN });

		await review.turnStoriesOff();

		expect(review.conversation.turns.at(-1)?.body).toBe('the story could not be stopped — the review fell over');
	});
});
