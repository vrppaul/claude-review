import { describe, it, expect, vi } from 'vitest';
import { ReviewStory } from '$lib/review/review-story.svelte';
import { fakeServer } from './fake-server';
import { storyHeld } from './story';

describe('the story a page holds', () => {
	it('is the one the review held when it was read last, though an earlier read is answered after it', async () => {
		const reads = fakeServer().hold('GET /api/story');
		const story = new ReviewStory(true, null);
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
		const story = new ReviewStory(true, storyHeld());

		await story.read();

		expect(story.held).toBeNull();
	});
});
