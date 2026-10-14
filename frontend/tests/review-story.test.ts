import { describe, it, expect, vi } from 'vitest';
import { ReviewStory, type StoryOpening } from '$lib/review/review-story.svelte';
import type { StoryResponse } from '$lib/types';
import { A_LATER_TAKE, FIRST_TAKE } from './diff';
import { fakeServer, SERVER_ERROR, takingStoryAskings } from './fake-server';
import { ASKED, codeMovedOn, storyHeld, storyResponse, TAKEN } from './story';

/** What a reader who opens the review for the first time has read through of its story. */
const NOTHING_READ: string[] = [];
/** A part of a story, as the page knows it: the same in a story told again. */
const A_PART = 'a part of the story';

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
		partsRead: NOTHING_READ,
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

		await story.read();

		expect(story.wait).toBeNull();
	});

	it('is what the reader waits on while a round has moved the code on under the story held, still drawn', () => {
		const story = pageStory({ held: MOVED_ON, asking: TAKEN });

		expect(story.wait).toEqual({ kind: 'writing', asking: TAKEN });
		expect(story.storyOrWait).toEqual({ kind: 'story', held: MOVED_ON });
	});

	it('lets a story be asked for over one a round moved the code on under', () => {
		expect(pageStory({ held: MOVED_ON }).canBeAskedFor).toBe(true);
	});
});

describe('the story a page holds', () => {
	it('is the one the review held when it was read last, though an earlier read is answered after it', async () => {
		const reads = fakeServer().hold('GET /api/story');
		const story = pageStory();
		const readFirst = story.read();
		const readLast = story.read();
		await vi.waitFor(() => expect(reads.requests).toHaveLength(2));

		reads.answer(1, storyResponse({ held: storyHeld({ title: 'Told second' }) }));
		reads.answer(0, storyResponse({ held: storyHeld({ title: 'Told first' }) }));
		await Promise.all([readFirst, readLast]);

		expect(story.held?.story.title).toBe('Told second');
	});

	it('is none once the review holds none', async () => {
		fakeServer().answer('GET /api/story', storyResponse());
		const story = pageStory({ held: storyHeld() });

		await story.read();

		expect(story.held).toBeNull();
	});
});

describe('whose numbers the lines of the story held carry', () => {
	it("are the review's own while the page reads the take the story was told of", () => {
		const story = pageStory({ held: storyHeld() });

		expect(story.numbering).toBe('the-reviews');
	});

	it("are another take's once the page reads another take of the change", () => {
		const story = pageStory({ held: storyHeld(), takeOnScreen: readingALaterTake });

		expect(story.numbering).toBe('another-takes');
	});

	it("are the review's own again once the story held is one told of the take the page reads", async () => {
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({}, { take: A_LATER_TAKE }) }));
		const story = pageStory({ held: storyHeld(), takeOnScreen: readingALaterTake });

		await story.read();

		expect(story.numbering).toBe('the-reviews');
	});
});

describe('the pieces of the story a page holds', () => {
	it('are laid out once for the story held, however often they are asked for', () => {
		const story = pageStory({ held: storyHeld() });

		expect(story.pieces).toBe(story.pieces);
	});

	it('are laid out afresh once another story is held', async () => {
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told again' }) }));
		const story = pageStory({ held: storyHeld() });
		const ofTheFirstStory = story.pieces;

		await story.read();

		expect(story.pieces).not.toBe(ofTheFirstStory);
	});

	it('are none while no story is held', () => {
		const story = pageStory();

		expect(story.pieces.keys).toEqual([]);
	});
});

describe('what the reader has read through of the story a page holds', () => {
	it('stands while another story the review was told is on its way: the one before is still held', async () => {
		const reads = fakeServer().hold('GET /api/story');
		const story = pageStory({ held: storyHeld(), partsRead: [A_PART] });

		void story.readAnother();
		await vi.waitFor(() => expect(reads.requests).toHaveLength(1));

		expect(story.progress.isRead(A_PART)).toBe(true);
	});

	it('is forgotten once that story is held: nothing of it is read yet', async () => {
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told again' }) }));
		const story = pageStory({ held: storyHeld(), partsRead: [A_PART] });

		await story.readAnother();

		expect(story.progress.isRead(A_PART)).toBe(false);
	});

	it('stands with the story before, where the other could not be read', async () => {
		fakeServer().refuse('GET /api/story', SERVER_ERROR);
		const story = pageStory({ held: storyHeld(), partsRead: [A_PART] });

		await story.readAnother().catch(() => undefined);

		expect(story.progress.isRead(A_PART)).toBe(true);
	});

	it('is forgotten once the other story is held after all, read when the page caught up', async () => {
		const server = fakeServer();
		server.refuse('GET /api/story', SERVER_ERROR);
		const story = pageStory({ held: storyHeld(), partsRead: [A_PART] });
		await story.readAnother().catch(() => undefined);
		server.answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told again' }) }));

		await story.read();

		expect(story.progress.isRead(A_PART)).toBe(false);
	});

	it('stands when the page reads the story again only to catch up, and of a story told again before that too', async () => {
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told again' }) }));
		const story = pageStory({ held: storyHeld() });
		await story.readAnother();
		story.progress.markRead(A_PART);

		await story.read();

		expect(story.progress.isRead(A_PART)).toBe(true);
	});

	it('is forgotten when the story held is the one the review was told: the draft kept what was read of the one before', () => {
		const story = pageStory({ held: storyHeld(), partsRead: [A_PART] });

		story.heldIsAnother();

		expect(story.progress.isRead(A_PART)).toBe(false);
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

		await story.readAnother().catch(() => undefined);

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

		await story.read();

		expect(story.arrival).toBe('none');
	});

	it('has no offer to put away: putting one away changes nothing', () => {
		const story = pageStory({ held: storyHeld() });

		story.putOfferAway();

		expect(story.arrival).toBe('none');
	});
});
