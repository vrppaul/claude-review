import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { said } from '../elements';
import { keepingSettings, takingStoryAskings, type FakeServer } from '../fake-server';
import { guideServerIntroducingFeedback } from '../guide-server';
import { handOverNext } from '../pushes';
import { openReview, settingsWritingStories, type Opened } from '../review';
import { settled } from '../settled';
import { storyHeld, storyResponse, TAKEN, toldChapter, toldStep } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one')])] })];
// The release serving the review, which the reader was shown already: no card of the guide's stands
const RELEASE = '1.5.0';
// A story of the change, told while the reader reads the files
const A_STORY = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('a.py', 1)])] });

/** A server that keeps how far the reader was shown around, Story introduced to them and Send feedback not. */
function serving(): FakeServer {
	return guideServerIntroducingFeedback(RELEASE);
}

/** Draw a review for a reader Send feedback was never introduced to, once the guide has heard so. */
async function drawn(opened: Opened = {}): Promise<Review> {
	const review = openReview({ files, facts: { release: RELEASE }, ...opened });
	await review.guide.open();
	render(ReviewScreen, { props: { review } });
	flushSync();
	return review;
}

describe('Send feedback introduced under Help', () => {
	it('takes the keyboard to Send feedback as it appears', async () => {
		serving();

		await drawn();
		await settled();

		expect(document.activeElement).toBe(screen.getByTestId('feedback-introduction-send'));
	});

	it('opens the card by Send feedback, and stands no more', async () => {
		serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('feedback-introduction-send'));

		expect(screen.getByTestId('feedback')).toBeTruthy();
		expect(screen.queryByTestId('feedback-introduction')).toBeNull();
	});

	it('is put away for this review by its cross, nothing kept, and the keyboard goes to Help', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('feedback-introduction-close'));
		await settled();

		expect(screen.queryByTestId('feedback-introduction')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('open-help'));
		expect(server.bodiesSentTo('PUT /api/guide')).toEqual([]);
	});

	it('says in its place that it is gone for good and where Send feedback still is, and keeps that', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();

		await user.click(screen.getByTestId('feedback-introduction-hide'));
		await settled();

		expect(said(screen.getByTestId('feedback-introduction-hidden'))).toBe(
			"Won't show again, in any review. Send feedback is still in Help. Undo"
		);
		expect(document.activeElement).toBe(screen.getByTestId('feedback-introduction-undo'));
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ feedback_introduced: true }]));
	});

	it('comes back by Undo, and Send feedback is kept as not introduced', async () => {
		const server = serving();
		const user = userEvent.setup();
		await drawn();
		await user.click(screen.getByTestId('feedback-introduction-hide'));

		await user.click(screen.getByTestId('feedback-introduction-undo'));

		expect(screen.getByTestId('feedback-introduction')).toBeTruthy();
		await vi.waitFor(() =>
			expect(server.bodiesSentTo('PUT /api/guide')).toEqual([
				{ feedback_introduced: true },
				{ feedback_introduced: false }
			])
		);
	});

	it('waits while the note of a story that arrived stands under the header, handing the keyboard it held to Help', async () => {
		const server = serving();
		takingStoryAskings(server);
		keepingSettings(server);
		const review = await drawn({ settings: await settingsWritingStories(server, 'without_asking'), asking: TAKEN });
		server.answer('GET /api/story', storyResponse({ held: A_STORY }));
		screen.getByTestId('feedback-introduction-send').focus();

		handOverNext(review, { type: 'story' });
		await settled();

		expect(screen.getByTestId('story-ready')).toBeTruthy();
		expect(screen.queryByTestId('feedback-introduction')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('open-help'));
	});
});
