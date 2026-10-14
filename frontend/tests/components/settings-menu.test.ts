import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import type { Review } from '$lib/review/review.svelte';
import { diffResponse } from '../diff';
import { keepingSettings, takingStoryAskings, type FakeServer } from '../fake-server';
import { inReview, openReview, settingsWithStoriesOn } from '../review';
import { settled } from '../settled';
import { TAKEN } from '../story';

describe('the settings', () => {
	let review: Review;
	let server: FakeServer;

	beforeEach(() => {
		// A server that answers the diff of one repository, takes any setting, and any story asked for or stopped
		server = takingStoryAskings();
		server.answer('GET /api/diff', diffResponse());
		keepingSettings(server);
		review = openReview();
	});

	it('keep the choices made once out of the header, behind the gear', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));
		expect(queryByTestId('layout-split')).toBeNull();

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('layout-split'));

		expect(review.settings.current.diff_layout).toBe('split');
	});

	it('say in the header that whitespace is hidden, and show it again from there', async () => {
		const user = userEvent.setup();
		await review.settings.change({ ignore_whitespace: true });
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));
		expect(getByTestId('whitespace-hidden').textContent).toContain('No whitespace');

		await user.click(getByTestId('show-whitespace'));

		expect(review.settings.current.ignore_whitespace).toBe(false);
		expect(queryByTestId('whitespace-hidden')).toBeNull();
	});

	it('turn stories on behind the gear, here and for every later review', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('stories'));

		expect(review.settings.current.stories).toBe(true);
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ stories: true }]);
	});

	it('ask the agent for a story of this review as stories are turned on behind the gear', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('stories'));
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('turn stories off again behind the gear, and stop the story being written', async () => {
		const user = userEvent.setup();
		review = openReview({ settings: await settingsWithStoriesOn(server), asking: TAKEN });
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('stories'));
		await settled();

		expect(review.settings.current.stories).toBe(false);
		expect(server.requestsTo('POST /api/story/cancel')).toHaveLength(1);
	});

	it('say beside the choice of stories what each one costs', async () => {
		const user = userEvent.setup();
		const { getByTestId, getByText } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));

		expect(getByText("Each story spends the agent's tokens")).toBeTruthy();
	});

	it('offer stories in a review no story can be told of too: the choice is for every review', async () => {
		const user = userEvent.setup();
		review = openReview({ facts: { takes_a_story: false } });
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));

		expect(getByTestId('stories')).toBeTruthy();
	});
});
