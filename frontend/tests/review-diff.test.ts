import { beforeEach, describe, it, expect } from 'vitest';
import { contextLine, addedLine, diffFile, diffResponse, hunk } from './diff';
import { fakeServer, keepingSettings, SERVER_ERROR } from './fake-server';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

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
	it('has nothing in view when the review holds no files', () => {
		expect(review.diff.files).toEqual([]);
		expect(review.diff.fileInView).toBeNull();
	});

	it('selects the first file of a diff that arrives', () => {
		review = openReview({ files });

		expect(review.diff.files).toHaveLength(2);
		expect(review.diff.fileInView).toBe('src/a.ts');
	});

	it('records the file scrolled into view', () => {
		review = openReview({ files });
		review.diff.markInView('src/b.ts');

		expect(review.diff.fileInView).toBe('src/b.ts');
	});

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

	it('keeps the files already worked through', async () => {
		fakeServer().answer('GET /api/diff', diffResponse());
		review.reading.setViewed('src/a.ts', true);

		await review.setIgnoreWhitespace(true);

		// Retaking the diff must not undo a reader's progress through it
		expect(review.reading.isViewed('src/a.ts')).toBe(true);
	});

	it('drops lines revealed against hunks a round replaced', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await review.diff.revealed.reveal('a.ts', 0, 1, 2, 0);
		expect(review.diff.revealed.revealedCount('a.ts', 0)).toBe(2);

		await review.diff.take();

		expect(review.diff.revealed.revealedCount('a.ts', 0)).toBe(0);
	});

	it('drops lines revealed against hunks whitespace renumbered', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await review.diff.revealed.reveal('a.ts', 0, 1, 2, 0);
		expect(review.diff.revealed.revealedCount('a.ts', 0)).toBe(2);

		await review.setIgnoreWhitespace(true);

		expect(review.diff.revealed.revealedCount('a.ts', 0)).toBe(0);
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
