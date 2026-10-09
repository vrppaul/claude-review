import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import type { DiffFile } from '$lib/types';
import { addedLine, diffFile, hunk, removedLine } from '../diff';
import { BAD_REQUEST, fakeServer } from '../fake-server';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** How many lines long the file is, as the server says when it hands a window of it. */
const FILE_LENGTH = 40;

const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([removedLine(30, 'x = 1'), addedLine(30, 'x = 2')], {
			header: '@@ -30,2 +30,2 @@',
			old_start: 30,
			new_start: 30
		})
	]
});

describe('widening the context around a hunk', () => {
	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	it('offers to show the lines the diff left out', () => {
		const { getByTestId } = render(FileSection, inReview(review, { file }));

		expect(getByTestId('expand-context').textContent).toContain('29 hidden lines');
	});

	it('reads the lines and shows them above the hunk', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/file-window', {
			start: 10,
			lines: ['before one', 'before two'],
			total: FILE_LENGTH
		});

		const { getByTestId, getByText } = render(FileSection, inReview(review, { file }));
		await user.click(getByTestId('expand-context'));

		expect(getByText('before one')).toBeTruthy();
		expect(getByText('before two')).toBeTruthy();
	});

	it('takes a gap this small in one go', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: [], total: FILE_LENGTH });

		const { getByTestId } = render(FileSection, inReview(review, { file }));
		await user.click(getByTestId('expand-context'));

		expect(server.requests).toMatchObject([
			{ path: '/api/file-window', query: { path: 'src/app.py', start: '1', end: '29' } }
		]);
	});

	it('reveals a large gap a piece at a time', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 481, lines: [], total: 900 });

		const distant: DiffFile = {
			...file,
			path: 'src/long.py',
			hunks: [{ ...file.hunks[0], new_start: 501, old_start: 501 }]
		};
		review = openReview({ files: [distant] });

		const { getByTestId } = render(FileSection, inReview(review, { file: distant }));
		expect(getByTestId('expand-context').textContent).toContain('of 500 hidden lines');

		await user.click(getByTestId('expand-context'));

		expect(server.requests).toMatchObject([
			{ path: '/api/file-window', query: { path: 'src/long.py', start: '481', end: '500' } }
		]);
	});

	it('says so when the file could not be read', async () => {
		const user = userEvent.setup();
		fakeServer().refuse('GET /api/file-window', BAD_REQUEST);

		const { getByTestId } = render(FileSection, inReview(review, { file }));
		await user.click(getByTestId('expand-context'));

		expect(getByTestId('expand-error')).toBeTruthy();
	});

	it('offers nothing when the hunk already starts at the top of the file', () => {
		const fromTop: DiffFile = {
			...file,
			path: 'src/top.py',
			hunks: [{ ...file.hunks[0], new_start: 1, old_start: 1 }]
		};
		review = openReview({ files: [fromTop] });

		const { queryByTestId } = render(FileSection, inReview(review, { file: fromTop }));

		expect(queryByTestId('hunk-gap')).toBeNull();
	});

	it('leaves plain files alone, since nothing of them is hidden', () => {
		const plain: DiffFile = { ...file, path: '/tmp/plan.md' };
		review = openReview({ files: [plain], facts: { mode: 'files' } });

		const { queryByTestId } = render(FileSection, inReview(review, { file: plain }));

		expect(queryByTestId('hunk-gap')).toBeNull();
	});

	it('takes the jump marker away once nothing is hidden any more', async () => {
		const user = userEvent.setup();
		// Every one of the 29 lines above the hunk
		fakeServer().answer('GET /api/file-window', {
			start: 1,
			lines: Array.from({ length: 29 }, (_, offset) => `line ${offset + 1}`),
			total: FILE_LENGTH
		});
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file }));
		expect(getByTestId('hunk-header')).toBeTruthy();

		await user.click(getByTestId('expand-context'));

		// The code now runs from the top of the file into the hunk without a
		// break, and a marker saying otherwise is punctuation mid-sentence
		expect(queryByTestId('hunk-header')).toBeNull();
		expect(queryByTestId('hunk-gap')).toBeNull();
	});
});
