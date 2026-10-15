import { describe, it, expect } from 'vitest';
import { ReviewStory, type StoryOpening } from '$lib/review/review-story.svelte';
import { stepSectionKey } from '$lib/review/story-keys';
import type { StoryResponse } from '$lib/types';
import { A_LATER_TAKE, FIRST_TAKE } from './diff';
import { fakeServer, SERVER_ERROR, takingStoryAskings } from './fake-server';
import { ASKED, codeMovedOn, readTheStoryAgain, storyHeld, storyResponse, TAKEN, toldChapter, toldStep } from './story';

/** A page that reads the first take of the change. */
function readingTheFirstTake(): number {
	return FIRST_TAKE;
}

/** A page that reads a later take: the diff was taken again. */
function readingALaterTake(): number {
	return A_LATER_TAKE;
}

/** A page of a review nobody is attached to. */
function nobodyAttached(): boolean {
	return false;
}

/** A page whose panel nobody reads: what the story says there is said to nobody. */
function saidToNobody(): void {}

/** A story held that a round moved the code on under. */
const MOVED_ON = storyHeld({}, { moved_on: codeMovedOn() });

/** What a review that holds a story answers of it. */
function holdingAStory(): StoryResponse {
	return storyResponse({ held: storyHeld() });
}

/**
 * The story of a page as it opens on a review that takes one: none held,
 * asked for or read, at the first take, with nobody attached, unless the
 * test says otherwise.
 */
function pageStory(given: Partial<StoryOpening> = {}): ReviewStory {
	return new ReviewStory({
		canBeTold: true,
		held: null,
		asking: null,
		takeOnScreen: readingTheFirstTake,
		agentAttached: nobodyAttached,
		sayInPanel: saidToNobody,
		...given
	});
}

describe('what stands where the story is read', () => {
	it('is what the reader waits on, while the review holds no story', () => {
		const story = pageStory({ asking: TAKEN });

		expect(story.storyOrWait).toEqual({ kind: 'wait', wait: { kind: 'writing', asking: TAKEN } });
	});

	it('is the story, once the review holds one', () => {
		const held = storyHeld();
		const story = pageStory({ held });

		expect(story.storyOrWait).toEqual({ kind: 'story', held });
	});
});

describe('asking the agent for a story', () => {
	it('sends the request to the review, which says to every page how the asking then stands', async () => {
		const server = takingStoryAskings();
		const story = pageStory();

		await story.askFor();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('says in the panel why the story could not be asked for', async () => {
		fakeServer().refuse('POST /api/story/request', SERVER_ERROR, 'the review fell over');
		const saidInPanel: string[] = [];
		const story = pageStory({ sayInPanel: (words) => saidInPanel.push(words) });

		await story.askFor();

		expect(saidInPanel).toEqual(['the story could not be asked for — the review fell over']);
	});
});

describe('stopping the story asked for', () => {
	it('sends the stop to the review', async () => {
		const server = takingStoryAskings();
		const story = pageStory({ asking: TAKEN });

		await story.stop();

		expect(server.requestsTo('POST /api/story/cancel')).toHaveLength(1);
	});

	it('says in the panel why the story could not be stopped', async () => {
		fakeServer().refuse('POST /api/story/cancel', SERVER_ERROR, 'the review fell over');
		const saidInPanel: string[] = [];
		const story = pageStory({
			asking: TAKEN,
			sayInPanel: (words) => saidInPanel.push(words)
		});

		await story.stop();

		expect(saidInPanel).toEqual(['the story could not be stopped — the review fell over']);
	});
});

describe('what a page holds of the asking for a story', () => {
	it('is how the review said it stood as the page opened', () => {
		const story = pageStory({ asking: TAKEN });

		expect(story.wait).toEqual({ kind: 'writing', asking: TAKEN });
	});

	it('is replaced whole by how the review says it stands next', () => {
		const story = pageStory({ asking: ASKED });

		story.learnAsking(TAKEN);

		expect(story.wait).toEqual({ kind: 'writing', asking: TAKEN });
	});

	it('is nothing to wait on once a story is held that is current', async () => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory({ asking: TAKEN });

		await readTheStoryAgain(story);

		expect(story.wait).toBeNull();
	});

	it('is what the reader waits on while a round has moved the code on under the story held, still drawn', () => {
		const story = pageStory({ held: MOVED_ON, asking: TAKEN });

		expect(story.wait).toEqual({ kind: 'writing', asking: TAKEN });
		expect(story.storyOrWait).toEqual({ kind: 'story', held: MOVED_ON });
	});
});

describe('the story a page holds', () => {
	it('is none once the review holds none', async () => {
		fakeServer().answer('GET /api/story', storyResponse());
		const story = pageStory({ held: storyHeld() });

		await readTheStoryAgain(story);

		expect(story.held).toBeNull();
	});
});

describe('the story a page opens on', () => {
	it('is the one the review held, of the take the page reads', () => {
		const held = storyHeld();

		expect(pageStory({ held }).held).toBe(held);
	});

	it('is none where the review held it on another take than the page read: it comes with that take’s diff', () => {
		const story = pageStory({ held: storyHeld(), takeOnScreen: readingALaterTake });

		expect(story.held).toBeNull();
	});
});

describe('the pieces of the story a page holds', () => {
	it('are those of another story once it is held', async () => {
		const toldAgain = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('b.py', 3)])] });
		fakeServer().answer('GET /api/story', storyResponse({ held: toldAgain }));
		const story = pageStory({ held: storyHeld() });

		await readTheStoryAgain(story);

		expect(story.pieces.keys).toEqual([stepSectionKey(toldStep('b.py', 3))]);
	});

	it('are none while no story is held', () => {
		const story = pageStory();

		expect(story.pieces.keys).toEqual([]);
	});
});

describe('a story told while the page is open', () => {
	it('is offered to the reader once it is held: they have not seen it', async () => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory();

		await story.readAnother();

		expect(story.arrival).toBe('offered');
	});

	it('is offered no more, and still unseen, once the reader put the offer away', async () => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory();
		await story.readAnother();

		story.putOfferAway();

		expect(story.arrival).toBe('put-away');
	});

	it.each([
		{ how: 'offered still', putAway: () => undefined },
		{ how: 'its offer put away', putAway: (story: ReviewStory) => story.putOfferAway() }
	])('is unseen no more once the reader has been shown it, $how', async ({ putAway }) => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory();
		await story.readAnother();
		putAway(story);

		story.seen();

		expect(story.arrival).toBe('none');
	});

	it('is offered again where another is told after the reader put the offer of the first away', async () => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory();
		await story.readAnother();
		story.putOfferAway();

		await story.readAnother();

		expect(story.arrival).toBe('offered');
	});

	it('has not arrived while it could not be read: there is nothing to show', async () => {
		fakeServer().refuse('GET /api/story', SERVER_ERROR);
		const story = pageStory();

		await story.readAnother();

		expect(story.arrival).toBe('none');
	});

	it('has not arrived where the review holds none after all', async () => {
		fakeServer().answer('GET /api/story', storyResponse());
		const story = pageStory();

		await story.readAnother();

		expect(story.arrival).toBe('none');
	});
});

describe('a story the page did not hear being told', () => {
	it('is not one that arrived unseen where the page read it as it opened', () => {
		const story = pageStory({ held: storyHeld() });

		expect(story.arrival).toBe('none');
	});

	it('is not one that arrived unseen where the page read it only to catch up', async () => {
		fakeServer().answer('GET /api/story', holdingAStory());
		const story = pageStory();

		await readTheStoryAgain(story);

		expect(story.arrival).toBe('none');
	});

	it('has no offer to put away: putting one away changes nothing', () => {
		const story = pageStory({ held: storyHeld() });

		story.putOfferAway();

		expect(story.arrival).toBe('none');
	});
});
