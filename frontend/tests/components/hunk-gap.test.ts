import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import FileSection from '$lib/components/FileSection.svelte';
import type { DiffFile } from '$lib/types';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine } from '../diff';
import { newComment } from '../new-comment';
import { keepingImages, paste, screenshot } from '../pasted-images';
import { BAD_REQUEST, fakeServer } from '../fake-server';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';
import { settled } from '../settled';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** How many lines long the file is, as the server says when it hands a window of it. */
const FILE_LENGTH = 40;

/** A hunk that replaces one line, this far down the file. */
function replacedAt(line: number) {
	return hunk([removedLine(line, 'x = 1'), addedLine(line, 'x = 2')], {
		header: `@@ -${line},1 +${line},1 @@`,
		old_start: line,
		new_start: line
	});
}

const file = diffFile({ path: 'src/app.py', hunks: [replacedAt(30)] });

describe('widening the context around a hunk', () => {
	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	it('offers to show the lines the diff left out', () => {
		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(getByTestId('expand-context').textContent).toContain('29 hidden lines');
	});

	it('reads the lines and shows them above the hunk', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/file-window', {
			start: 10,
			lines: ['before one', 'before two'],
			total: FILE_LENGTH
		});

		const { getByTestId, getByText } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		await user.click(getByTestId('expand-context'));

		expect(getByText('before one')).toBeTruthy();
		expect(getByText('before two')).toBeTruthy();
	});

	it('takes a gap this small in one go', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: [], total: FILE_LENGTH });

		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));
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
			hunks: [replacedAt(501)]
		};
		review = openReview({ files: [distant] });

		const { getByTestId } = render(FileSection, inReview(review, { file: distant, scrollRoot: null }));
		expect(getByTestId('expand-context').textContent).toContain('of 500 hidden lines');

		await user.click(getByTestId('expand-context'));

		expect(server.requests).toMatchObject([
			{ path: '/api/file-window', query: { path: 'src/long.py', start: '481', end: '500' } }
		]);
	});

	it('says so when the file could not be read', async () => {
		const user = userEvent.setup();
		fakeServer().refuse('GET /api/file-window', BAD_REQUEST);

		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		await user.click(getByTestId('expand-context'));

		expect(getByTestId('expand-error')).toBeTruthy();
	});

	it('offers nothing when the hunk already starts at the top of the file', () => {
		const fromTop: DiffFile = {
			...file,
			path: 'src/top.py',
			hunks: [replacedAt(1)]
		};
		review = openReview({ files: [fromTop] });

		const { queryByTestId } = render(FileSection, inReview(review, { file: fromTop, scrollRoot: null }));

		expect(queryByTestId('hunk-gap')).toBeNull();
	});

	it('leaves plain files alone, since nothing of them is hidden', () => {
		const plain: DiffFile = { ...file, path: '/tmp/plan.md' };
		review = openReview({ files: [plain], facts: { mode: 'files' } });

		const { queryByTestId } = render(FileSection, inReview(review, { file: plain, scrollRoot: null }));

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
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		expect(getByTestId('hunk-header')).toBeTruthy();

		await user.click(getByTestId('expand-context'));

		// The code now runs from the top of the file into the hunk without a
		// break, and a marker saying otherwise is punctuation mid-sentence
		expect(queryByTestId('hunk-header')).toBeNull();
		expect(queryByTestId('hunk-gap')).toBeNull();
	});
});

describe('lines asked for while the file is drawn again', () => {
	it('are asked for once, and drawn once', async () => {
		const user = userEvent.setup();
		review = openReview({ files: [file] });
		const windows = fakeServer().hold('GET /api/file-window');
		const { getByTestId, getAllByText } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		await user.click(getByTestId('expand-context'));

		// Folded and opened while the lines are on their way, and asked for again
		await user.click(getByTestId('collapse-file'));
		await user.click(getByTestId('collapse-file'));
		expect(getByTestId('expand-context').textContent).toContain('Reading');
		await user.click(getByTestId('expand-context'));
		windows.answer(0, { start: 1, lines: ['read once'], total: FILE_LENGTH });
		await settled();

		expect(windows.requests).toHaveLength(1);
		expect(getAllByText('read once')).toHaveLength(1);
	});
});

describe('lines asked for just before a new diff lands', () => {
	it('stay out of the new diff, whose lines are counted afresh', async () => {
		const user = userEvent.setup();
		review = openReview({ files: [file] });
		const server = fakeServer();
		const windows = server.hold('GET /api/file-window');
		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('expand-context'));

		// A round lands while the lines are on their way: the file now changes
		// above the hunk too, so what was hidden above it is not hidden any more
		server.answer('GET /api/diff', diffResponse({ files: [{ ...file, hunks: [replacedAt(15), replacedAt(30)] }] }));
		await review.diff.take();
		windows.answer(0, { start: 1, lines: ['read for the last diff'], total: FILE_LENGTH });
		await settled();

		expect(getByTestId('diff-view').textContent).not.toContain('read for the last diff');
	});
});

describe('what hangs under a line, when lines are revealed above it', () => {
	/** Two hunks, far apart: lines 30 and 60 replaced, each with an unchanged line after it. */
	const twoHunks = diffFile({
		path: 'src/app.py',
		hunks: [
			hunk([removedLine(30, 'x = 1'), addedLine(30, 'x = 2'), contextLine(31, 31, 'kept = 31')], {
				old_start: 30,
				new_start: 30
			}),
			hunk([removedLine(60, 'y = 1'), addedLine(60, 'y = 2'), contextLine(61, 61, 'kept = 61')], {
				old_start: 60,
				new_start: 60
			})
		]
	});
	// The lines read in above the first hunk
	const revealedAbove = Array.from({ length: 20 }, (_, offset) => `revealed ${10 + offset}`);

	/** The text of the row right above an element drawn under a line. */
	function rowAbove(element: HTMLElement): string {
		return element.closest('tr')?.previousElementSibling?.textContent ?? '';
	}

	/** Reveal lines above the first hunk. */
	async function revealAboveTheFirstHunk(user: ReturnType<typeof userEvent.setup>): Promise<void> {
		await user.click(screen.getAllByTestId('expand-context')[0]);
		await settled();
	}

	beforeEach(() => {
		review = openReview({ files: [twoHunks] });
		keepingImages().answer('GET /api/file-window', { start: 10, lines: revealedAbove, total: FILE_LENGTH });
	});

	it('keeps the comment being written under its own line, words and all', async () => {
		const user = userEvent.setup();
		const { getAllByTestId, getByTestId } = render(FileSection, inReview(review, { file: twoHunks, scrollRoot: null }));
		const line61 = getAllByTestId('line-gutter').find((gutter) => gutter.textContent?.trim() === '61');
		if (!line61) throw new Error('Line 61 is not drawn');
		await user.click(line61);
		await user.type(getByTestId('comment-input'), 'half a thought');

		await revealAboveTheFirstHunk(user);

		const field = getByTestId('comment-input') as HTMLTextAreaElement;
		expect(field.value).toBe('half a thought');
		expect(rowAbove(field)).toContain('kept = 61');
	});

	it('keeps a reply being written, and what was pasted into it', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'src/app.py', startLine: 31, body: 'why kept' }));
		const { getAllByTestId, getByTestId } = render(FileSection, inReview(review, { file: twoHunks, scrollRoot: null }));
		await user.click(getByTestId('open-reply'));
		await user.type(getByTestId('comment-input'), 'my reply');
		await paste(getByTestId('comment-input'), screenshot());
		await within(getByTestId('comment-thread')).findByTestId('attached-image');

		await revealAboveTheFirstHunk(user);

		expect((getByTestId('comment-input') as HTMLTextAreaElement).value).toBe('my reply');
		expect(getAllByTestId('attached-image')).toHaveLength(1);
	});
});
