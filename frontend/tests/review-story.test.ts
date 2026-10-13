import { describe, it, expect, vi } from 'vitest';
import { ReviewStory } from '$lib/review/review-story.svelte';
import { A_LATER_TAKE, FIRST_TAKE } from './diff';
import { fakeServer } from './fake-server';
import { storyHeld } from './story';

/** What a reader who opens the review for the first time has read through of its story. */
const NOTHING_READ: string[] = [];

/** A page that reads the first take of the change. */
function readingTheFirstTake(): number {
	return FIRST_TAKE;
}

/** A page that reads a later take: the diff was taken again. */
function readingALaterTake(): number {
	return A_LATER_TAKE;
}

describe('the story a page holds', () => {
	it('is the one the review held when it was read last, though an earlier read is answered after it', async () => {
		const reads = fakeServer().hold('GET /api/story');
		const story = new ReviewStory(true, null, readingTheFirstTake, NOTHING_READ);
		const readFirst = story.read();
		const readLast = story.read();
		await vi.waitFor(() => expect(reads.requests).toHaveLength(2));

		reads.answer(1, { held: storyHeld({ title: 'Told second' }) });
		reads.answer(0, { held: storyHeld({ title: 'Told first' }) });
		await Promise.all([readFirst, readLast]);

		expect(story.held?.story.title).toBe('Told second');
	});

	it('is none once the review holds none', async () => {
		fakeServer().answer('GET /api/story', { held: null });
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake, NOTHING_READ);

		await story.read();

		expect(story.held).toBeNull();
	});
});

describe('whose numbers the lines of the story held carry', () => {
	it("are the review's own while the page reads the take the story was told of", () => {
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake, NOTHING_READ);

		expect(story.numbering).toBe('the-reviews');
	});

	it("are another take's once the page reads another take of the change", () => {
		const story = new ReviewStory(true, storyHeld(), readingALaterTake, NOTHING_READ);

		expect(story.numbering).toBe('another-takes');
	});

	it("are the review's own again once the story held is one told of the take the page reads", async () => {
		fakeServer().answer('GET /api/story', { held: storyHeld({}, { take: A_LATER_TAKE }) });
		const story = new ReviewStory(true, storyHeld(), readingALaterTake, NOTHING_READ);

		await story.read();

		expect(story.numbering).toBe('the-reviews');
	});
});

describe('the pieces of the story a page holds', () => {
	it('are laid out once for the story held, however often they are asked for', () => {
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake, NOTHING_READ);

		expect(story.pieces).toBe(story.pieces);
	});

	it('are laid out afresh once another story is held', async () => {
		fakeServer().answer('GET /api/story', { held: storyHeld({ title: 'Told again' }) });
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake, NOTHING_READ);
		const ofTheFirstStory = story.pieces;

		await story.read();

		expect(story.pieces).not.toBe(ofTheFirstStory);
	});

	it('are none while no story is held', () => {
		const story = new ReviewStory(true, null, readingTheFirstTake, NOTHING_READ);

		expect(story.pieces.keys).toEqual([]);
	});
});
