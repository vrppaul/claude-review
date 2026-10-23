import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import type { Review } from '$lib/review/review.svelte';
import { diffResponse } from '../diff';
import { keepingSettings, takingStoryAskings, type FakeServer } from '../fake-server';
import { inReview, openReview, settingsWritingStories } from '../review';
import { settled } from '../settled';

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

	it('say in the header that whitespace is hidden, and show it again when that is pressed', async () => {
		const user = userEvent.setup();
		await review.settings.change({ ignore_whitespace: true });
		const { getByTestId, queryByTestId } = render(ReviewHeader, inReview(review));
		expect(getByTestId('whitespace-hidden').textContent).toContain('No whitespace');

		await user.click(getByTestId('whitespace-hidden'));

		expect(review.settings.current.ignore_whitespace).toBe(false);
		expect(queryByTestId('whitespace-hidden')).toBeNull();
	});

	it('name the button that says whitespace is hidden by what pressing it does, for whoever cannot see it', async () => {
		await review.settings.change({ ignore_whitespace: true });
		const { getByRole } = render(ReviewHeader, inReview(review));

		expect(getByRole('button', { name: 'Show whitespace changes again' })).toBeTruthy();
	});

	it('write stories without asking once it is chosen behind the gear, here and for every later review', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('write-without-asking'));

		expect(review.settings.current.story_writing).toBe('without_asking');
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ story_writing: 'without_asking' }]);
	});

	it('choose nothing at a press on writing as the review opens while every story is asked first: it is locked', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('write-as-the-review-opens'));

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([]);
	});

	it('hide whitespace changes behind the gear, taking the diff again without them', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('ignore-whitespace'));
		await settled();

		expect(server.requestsTo('GET /api/diff').map((request) => request.query.ignore_whitespace)).toEqual(['true']);
	});

	it('tick on a new reply once it is chosen behind the gear', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('reply-sound'));

		expect(review.settings.current.sound_on_replies).toBe(true);
	});

	it("write each review's story as it opens once it is chosen behind the gear, stories being written unasked", async () => {
		const user = userEvent.setup();
		review = openReview({ settings: await settingsWritingStories(server, 'without_asking') });
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('write-as-the-review-opens'));

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ story_writing: 'as_the_review_opens' }]);
	});

	it('ask before every story again once writing unasked is unticked, writing as the review opens going with it', async () => {
		const user = userEvent.setup();
		review = openReview({ settings: await settingsWritingStories(server, 'as_the_review_opens') });
		const { getByTestId } = render(ReviewHeader, inReview(review));

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('write-without-asking'));

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ story_writing: 'ask_first' }]);
		expect((getByTestId('write-as-the-review-opens') as HTMLInputElement).checked).toBe(false);
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

		expect(getByTestId('write-without-asking')).toBeTruthy();
	});
});
