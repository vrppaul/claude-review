import { describe, it, expect } from 'vitest';
import { keepingSettings, takingStoryAskings, type FakeServer } from './fake-server';
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

	it.each([
		{ where: 'none is held or asked for', opened: {} },
		{ where: 'the reader stopped the one asked for', opened: { asking: STOPPED } }
	])('asks for no story itself where $where: the server asks, and says so', async ({ opened }) => {
		const server = serving();
		const review = openReview(opened);

		await review.turnStoriesOn();

		expect(server.requestsTo('POST /api/story/request')).toEqual([]);
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
	])('stops no story itself, $awaited: the server stops it, and says so', async ({ asking }) => {
		const server = serving();
		const review = openReview({ settings: await settingsWithStoriesOn(server), asking });

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
});
