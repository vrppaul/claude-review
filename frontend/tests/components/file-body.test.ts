import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileBody from '$lib/components/FileBody.svelte';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine } from '../diff';
import { fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

/** A change to line 30 of a file: nothing above it is in the diff. */
const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([removedLine(30, 'gone = 1'), addedLine(30, 'there = 2'), contextLine(31, 31, 'kept = 3')], {
			old_start: 30,
			new_start: 30
		})
	]
});

/** How a story step draws a file: as lines, on the review's own removed lines, with gaps not to be read into. */
const AS_A_STEP = { file, language: null, view: 'raw', reviewOwnsRemovedLines: true, revealed: null } as const;

beforeEach(() => {
	review = openReview({ files: [file] });
});

describe('a file drawn where what the diff left out is not to be read in', () => {
	it('says how many lines it leaves out, and offers nothing to show them', () => {
		const { getByTestId, queryByTestId } = render(FileBody, inReview(review, AS_A_STEP));

		expect(getByTestId('hunk-gap').textContent).toContain('29 unchanged lines');
		expect(queryByTestId('expand-context')).toBeNull();
	});

	it('says the same in two columns', () => {
		const { getByTestId, queryByTestId } = render(FileBody, inReview(review, { ...AS_A_STEP, view: 'split' }));

		expect(getByTestId('hunk-gap').textContent).toContain('29 unchanged lines');
		expect(queryByTestId('expand-context')).toBeNull();
	});
});

describe("a file drawn on the review's own removed lines, whatever base is on screen", () => {
	beforeEach(async () => {
		fakeServer().answer('GET /api/diff', diffResponse({ files: [file], phrase: 'changes since round 1' }));
		await review.diff.setBase('round:1');
	});

	it('takes a comment on a removed line', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(FileBody, inReview(review, AS_A_STEP));

		await user.click(within(rowHolding('gone = 1')).getAllByRole('button')[0]);
		await user.type(getByTestId('comment-input'), 'why did this go');
		await user.click(getByTestId('save-comment'));

		expect(review.threads.all[0].anchor).toMatchObject({ side: 'old', start_line: 30 });
	});

	it('draws the threads on removed lines', () => {
		review.threads.add(newComment({ file: file.path, side: 'old', startLine: 30, body: 'why did this go' }));

		const { getByText } = render(FileBody, inReview(review, AS_A_STEP));

		expect(getByText('why did this go')).toBeTruthy();
	});
});

/** The row that holds this text. */
function rowHolding(text: string): HTMLElement {
	const row = screen.getByText(text).closest('tr');
	if (!row) throw new Error(`No row holds ${text}`);
	return row;
}

describe('a file drawn as whoever draws it says', () => {
	it("is drawn in two columns when told to, whatever the reader's own layout", () => {
		const { getByTestId, queryByTestId } = render(FileBody, inReview(review, { ...AS_A_STEP, view: 'split' }));

		expect(review.settings.current.diff_layout).toBe('unified');
		expect(getByTestId('split-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});
});

describe('the keyboard in one column', () => {
	it("stops on the number each line shows: a removed line's is on the old side", () => {
		render(FileBody, inReview(review, AS_A_STEP));

		const stops = screen.getAllByTestId('line-gutter');

		expect(stops.map((stop) => stop.textContent?.trim())).toEqual(['30', '30', '31']);
		expect(stops[0].getAttribute('aria-label')).toBe('Comment on removed line 30');
	});
});
