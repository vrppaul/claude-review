import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { addedLine, contextLine, diffFile, hunk, removedLine } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const file = diffFile({
	path: 'src/app.ts',
	hunks: [
		hunk([
			contextLine(1, 1, 'const a = 1;'),
			removedLine(2, 'const b = 2;'),
			addedLine(2, 'const b = 3;'),
			addedLine(3, 'const c = 4;')
		])
	]
});

/** The row of the two columns that holds this text, on either side. */
function rowHolding(text: string): HTMLElement {
	const row = screen
		.getAllByTestId('split-row')
		.find((candidate) => candidate.textContent?.includes(text));
	if (!row) throw new Error(`No row holds ${text}`);
	return row;
}

/** Read the diff across two columns, as the reader chose in the settings. */
async function inTwoColumns(): Promise<void> {
	keepingSettings(fakeServer());
	await review.settings.change({ diff_layout: 'split' });
}

describe('split layout', () => {
	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	it('reads down one column until asked for two', () => {
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file }));

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('split-view')).toBeNull();
	});

	it('faces the old version against the new one', async () => {
		await inTwoColumns();

		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file }));

		expect(getByTestId('split-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('shows both versions of a replaced line on one row', async () => {
		await inTwoColumns();

		render(FileSection, inReview(review, { file }));
		const replaced = rowHolding('const b = 2;');

		expect(within(replaced).getByTestId('split-old-code').textContent).toContain('const b = 2;');
		expect(within(replaced).getByTestId('split-new-code').textContent).toContain('const b = 3;');
	});

	it('leaves the old side of a pure insertion empty', async () => {
		await inTwoColumns();

		render(FileSection, inReview(review, { file }));
		const inserted = rowHolding('const c = 4;');

		expect(within(inserted).getByTestId('split-old-code').textContent?.trim()).toBe('');
		expect(within(inserted).getByTestId('split-new-code').textContent).toContain('const c = 4;');
	});

	it('files a comment left on the old side as a removal', async () => {
		const user = userEvent.setup();
		await inTwoColumns();

		const { getByTestId } = render(FileSection, inReview(review, { file }));
		await user.click(within(rowHolding('const b = 2;')).getByTestId('old-line-gutter'));
		await user.click(document.body);
		await user.type(getByTestId('comment-input'), 'why did this go');
		await user.click(getByTestId('save-comment'));

		expect(review.threads.all[0].anchor).toMatchObject({ side: 'old', start_line: 2 });
	});

	it('keeps a comment made in one layout visible in the other', async () => {
		review.threads.add(newComment({ file: 'src/app.ts', startLine: 2, body: 'tighten this' }));
		await inTwoColumns();

		const { getByText } = render(FileSection, inReview(review, { file }));

		expect(getByText('tighten this')).toBeTruthy();
	});

	it('shows a comment on an unchanged line once, not once per column', async () => {
		// An unchanged line is the same line on both sides of the row
		review.threads.add(newComment({ file: 'src/app.ts', startLine: 1, body: 'name this' }));
		await inTwoColumns();

		const { getAllByText } = render(FileSection, inReview(review, { file }));

		expect(getAllByText('name this')).toHaveLength(1);
	});

	it('still shows a comment on each side of a replacement', async () => {
		review.threads.add(newComment({ file: 'src/app.ts', side: 'old', startLine: 2, body: 'why gone' }));
		review.threads.add(newComment({ file: 'src/app.ts', side: 'new', startLine: 2, body: 'why this' }));
		await inTwoColumns();

		const { getAllByText } = render(FileSection, inReview(review, { file }));

		expect(getAllByText('why gone')).toHaveLength(1);
		expect(getAllByText('why this')).toHaveLength(1);
	});
});

describe('reaching every row from the keyboard in two columns', () => {
	const removal = diffFile({
		path: 'src/gone.ts',
		hunks: [
			hunk([
				contextLine(1, 1, 'const a = 1;'),
				removedLine(2, 'const b = 2;'),
				contextLine(3, 2, 'const c = 3;')
			])
		]
	});

	beforeEach(async () => {
		review = openReview({ files: [removal] });
		await inTwoColumns();
	});

	it('stops once on every row, a removed line with nothing beside it included', () => {
		const { getAllByTestId } = render(FileSection, inReview(review, { file: removal }));

		const stops = getAllByTestId('line-gutter');

		expect(stops.map((stop) => stop.textContent?.trim())).toEqual(['1', '2', '2']);
		expect(stops[1].getAttribute('aria-label')).toBe('Comment on removed line 2');
		expect(stops.every((stop) => stop.tabIndex === 0)).toBe(true);
	});
});
