import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { contextLine, diffFile, hunk } from '../diff';
import { newComment } from '../new-comment';
import { openReview } from '../review';

const files = [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x = 1')])] })];

describe('comments picked up from before a reload', () => {
	it('are said once, until the reader puts the notice away', async () => {
		const user = userEvent.setup();
		openReview({ files }).threads.add(newComment({ file: 'a.py', body: 'kept' }));
		const review = openReview({ files });

		const { getByTestId, queryByTestId } = render(ReviewScreen, { props: { review } });
		expect(getByTestId('restored-notice').textContent).toContain('Picked up 1 comment you had not sent yet.');

		await user.click(getByTestId('dismiss-restored'));

		expect(queryByTestId('restored-notice')).toBeNull();
	});
});
