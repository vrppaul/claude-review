import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import type { Review } from '$lib/review/review.svelte';
import { diffResponse } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { inReview, openReview } from '../review';

describe('the settings', () => {
	let review: Review;

	beforeEach(() => {
		// A server that answers the diff of one repository, and takes any setting
		const server = fakeServer();
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
});
