import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { CheckFailure } from '$lib/types';
import { failedCheck, failure } from '../checks';
import { contextLine, diffFile, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { openReview } from '../review';
import { settled } from '../settled';

// A file whose lines 1 to 3 and 50 the diff holds: 4 to 49 lie between its hunks, unchanged
const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([contextLine(1, 1, 'one'), contextLine(2, 2, 'two'), contextLine(3, 3, 'three')]),
		hunk([contextLine(50, 50, 'fifty')], { header: '', old_start: 50, new_start: 50 })
	]
});

/** The review on screen, holding a check that failed where these say. */
function onScreenFailing(failures: CheckFailure[]): Review {
	const review = openReview({ files: [file], facts: { checks: [failedCheck(failures, { name: 'pytest' })] } });
	render(ReviewScreen, { props: { review } });
	return review;
}

/** Press where a check failed, in the pane the header's chip opens. */
async function pressFailure(): Promise<void> {
	const user = userEvent.setup({ delay: null });
	await user.click(screen.getByTestId('checks'));
	await user.click(within(screen.getByTestId('checks-pane')).getByRole('button', { name: /app\.py/ }));
	await settled();
}

describe('going to where a check failed', () => {
	it('takes the reader to the line, the keyboard on its number, and puts the pane away', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('2');
		expect(screen.queryByTestId('checks-pane')).toBeNull();
	});

	it('unfolds the file the line is in', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 3 })]);
		review.reading.toggleFolded('src/app.py');

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('3');
	});

	it('reads in the lines the diff left out to reach a line between its hunks', async () => {
		const server = fakeServer();
		const read = Array.from({ length: 33 }, (_, offset) => `line ${offset + 4}`);
		server.answer('GET /api/file-window', { start: 4, lines: read, total: 50 });
		onScreenFailing([failure({ path: 'src/app.py', line: 16 })]);

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('16');
	});

	it('says where a check failed in a file the review does not hold, with no way there', async () => {
		onScreenFailing([failure({ path: 'src/elsewhere.py', line: 2, what: 'test_elsewhere' })]);
		await userEvent.setup({ delay: null }).click(screen.getByTestId('checks'));

		const pane = screen.getByTestId('checks-pane');

		expect(within(pane).getByTestId('check-failure').textContent).toContain('test_elsewhere');
		expect(within(pane).queryByRole('button', { name: /elsewhere/ })).toBeNull();
	});
});
