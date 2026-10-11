import { beforeEach, describe, it, expect } from 'vitest';
import { contextLine, addedLine, diffFile, diffResponse, hunk } from './diff';
import { fakeServer, keepingSettings, SERVER_ERROR } from './fake-server';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';
import { SEND_LIMITS } from './pasted-images';
import { gapAbove, type GapRead, hunkKey, readOf } from '$lib/utils/expansions';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** A hunk of one added line, this far down the file. */
function hunkAt(newStart: number) {
	return hunk([addedLine(newStart, 'added')], { old_start: newStart, new_start: newStart });
}

/** Read lines of a.ts into a gap, as its controls do. */
async function reveal(read: GapRead | null): Promise<void> {
	if (read === null) throw new Error('Nothing in the gap to read');
	await review.diff.revealed.reveal('a.ts', read);
}

/** Read in the lines above a hunk at line 3 of a.ts, as its gap's ↑ does. */
async function revealAboveTheHunk(): Promise<void> {
	await reveal(readOf(gapAbove(hunkAt(3), undefined), 'up', SEND_LIMITS.max_window_lines));
}

const files = [
	diffFile({
		path: 'src/a.ts',
		hunks: [hunk([contextLine(1, 1, 'const x = 1;'), addedLine(2, 'const y = 2;')])]
	}),
	diffFile({ path: 'src/b.ts', status: 'added' })
];

/** Where the page keeps how a markdown file is shown. */
const CONTENT_VIEW_KEPT_HERE = 'claude-review:content-view';

describe('the diff on screen', () => {
	it('is read from the server', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files }));

		await review.diff.take();

		expect(review.diff.files.map((file) => file.path)).toEqual(['src/a.ts', 'src/b.ts']);
		expect(server.requests).toEqual([{ method: 'GET', path: '/api/diff', query: {}, body: null }]);
	});

	it('says so when it cannot be read', async () => {
		fakeServer().fail('GET /api/diff', SERVER_ERROR);

		await expect(review.diff.take()).rejects.toThrow(`Could not take the diff: ${SERVER_ERROR}`);
	});

	it('reads as a diff until told otherwise', () => {
		expect(review.mode).toBe('diff');
	});

	it('reads plain files as files', () => {
		review = openReview({ files: files, facts: { mode: 'files' } });

		expect(review.mode).toBe('files');
	});

	it('reads a transcript as one', () => {
		review = openReview({ files: files, facts: { mode: 'transcript' } });

		expect(review.mode).toBe('transcript');
	});
});

describe('how a markdown file is shown', () => {
	it('is the raw text until the reader asks otherwise', () => {
		expect(review.layout.contentView.mode).toBe('raw');
	});

	it('is the way the reader picked', () => {
		review.layout.contentView.set('preview');

		expect(review.layout.contentView.mode).toBe('preview');
	});

	it('is remembered in this browser', () => {
		review.layout.contentView.set('side-by-side');

		expect(localStorage.getItem(CONTENT_VIEW_KEPT_HERE)).toBe('side-by-side');
	});

	it("stays across reviews — it is the reader's, not the review's", () => {
		review.layout.contentView.set('side-by-side');

		review = openReview();

		expect(review.layout.contentView.mode).toBe('side-by-side');
	});
});

describe('retaking the diff', () => {
	it('asks git to leave whitespace-only changes out', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse());

		await review.setIgnoreWhitespace(true);

		expect(server.requestsTo('GET /api/diff')).toMatchObject([{ query: { ignore_whitespace: 'true' } }]);
		expect(review.settings.current.ignore_whitespace).toBe(true);
	});

	it('says in the panel when the diff cannot be taken again without whitespace', async () => {
		fakeServer().fail('GET /api/diff', SERVER_ERROR);

		await review.setIgnoreWhitespace(true);

		expect(review.conversation.turns.at(-1)?.body).toMatch(/the diff could not be taken again/);
	});

	it('keeps the files already worked through', async () => {
		fakeServer().answer('GET /api/diff', diffResponse());
		review.reading.setViewed('src/a.ts', true);

		await review.setIgnoreWhitespace(true);

		// Retaking the diff must not undo a reader's progress through it
		expect(review.reading.isViewed('src/a.ts')).toBe(true);
	});

	it("keeps lines read up from a hunk in the file's order, the later read above the earlier", async () => {
		const server = fakeServer();
		const gap = gapAbove(hunkAt(50), undefined);
		server.answer('GET /api/file-window', { start: 30, lines: ['line 30', 'line 31'], total: 60 });
		await reveal(readOf(gap, 'up', SEND_LIMITS.max_window_lines));
		server.answer('GET /api/file-window', { start: 10, lines: ['line 10', 'line 11'], total: 60 });
		await reveal(readOf(gap, 'up', SEND_LIMITS.max_window_lines));

		const above = review.diff.revealed.forFile('a.ts').above.get(gap.key) ?? [];
		expect(above.map((line) => line.content)).toEqual(['line 10', 'line 11', 'line 30', 'line 31']);
	});

	it("keeps lines read down from a hunk in the file's order, the later read below the earlier", async () => {
		const server = fakeServer();
		const gap = gapAbove(hunkAt(50), hunkAt(3));
		server.answer('GET /api/file-window', { start: 4, lines: ['line 4', 'line 5'], total: 60 });
		await reveal(readOf(gap, 'down', SEND_LIMITS.max_window_lines));
		server.answer('GET /api/file-window', { start: 24, lines: ['line 24', 'line 25'], total: 60 });
		await reveal(readOf(gap, 'down', SEND_LIMITS.max_window_lines));

		const below = review.diff.revealed.forFile('a.ts').below.get(hunkKey(hunkAt(3))) ?? [];
		expect(below.map((line) => line.content)).toEqual(['line 4', 'line 5', 'line 24', 'line 25']);
	});

	it('drops lines revealed against hunks a round replaced', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await revealAboveTheHunk();
		expect(review.diff.revealed.forFile('a.ts').above.size).toBe(1);

		await review.diff.take();

		expect(review.diff.revealed.forFile('a.ts').above.size).toBe(0);
	});

	it('drops lines revealed against hunks whitespace renumbered', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await revealAboveTheHunk();
		expect(review.diff.revealed.forFile('a.ts').above.size).toBe(1);

		await review.setIgnoreWhitespace(true);

		expect(review.diff.revealed.forFile('a.ts').above.size).toBe(0);
	});
});

describe('how a diff is laid out', () => {
	it("is kept with the reader's settings, for every review", async () => {
		const server = fakeServer();
		keepingSettings(server);

		await review.settings.change({ diff_layout: 'split' });

		expect(review.settings.current.diff_layout).toBe('split');
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ diff_layout: 'split' }]);
	});

	it('stays across reviews, which are not what it belongs to', async () => {
		keepingSettings(fakeServer());
		await review.settings.change({ diff_layout: 'split' });

		review = openReview({ settings: review.settings });

		expect(review.settings.current.diff_layout).toBe('split');
	});
});
