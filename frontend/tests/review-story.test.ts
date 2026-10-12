import { describe, it, expect, vi } from 'vitest';
import { ReviewStory } from '$lib/review/review-story.svelte';
import { A_LATER_TAKE, FIRST_TAKE } from './diff';
import { fakeServer } from './fake-server';
import { storyHeld } from './story';

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
		const story = new ReviewStory(true, null, readingTheFirstTake);
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
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake);

		await story.read();

		expect(story.held).toBeNull();
	});
});

describe('whose numbers the lines of the story held carry', () => {
	it("are the review's own while the page reads the take the story was told of", () => {
		const story = new ReviewStory(true, storyHeld(), readingTheFirstTake);

		expect(story.numbering).toBe('the-reviews');
	});

	it("are another take's once the page reads another take of the change", () => {
		const story = new ReviewStory(true, storyHeld(), readingALaterTake);

		expect(story.numbering).toBe('another-takes');
	});

	it("are the review's own again once the story held is one told of the take the page reads", async () => {
		fakeServer().answer('GET /api/story', { held: storyHeld({}, { take: A_LATER_TAKE }) });
		const story = new ReviewStory(true, storyHeld(), readingALaterTake);

		await story.read();

		expect(story.numbering).toBe('the-reviews');
	});
});
