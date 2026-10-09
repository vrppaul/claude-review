import { describe, it, expect } from 'vitest';
import { diffStore } from '$lib/stores/diff.svelte';
import { expansionStore } from '$lib/stores/expansions.svelte';
import { contextLine, addedLine, diffFile, diffResponse, hunk, reviewResponse } from './diff';
import { fakeServer, keepingSettings, SERVER_ERROR } from './fake-server';

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
	it('starts with no files and none selected', () => {
		expect(diffStore.files).toEqual([]);
		expect(diffStore.selectedPath).toBeNull();
		expect(diffStore.selectedFile).toBeUndefined();
	});

	it('selects the first file of a diff that arrives', () => {
		diffStore.setFiles(files, 'diff');

		expect(diffStore.files).toHaveLength(2);
		expect(diffStore.selectedPath).toBe('src/a.ts');
		expect(diffStore.selectedFile?.path).toBe('src/a.ts');
	});

	it('records the file scrolled into view', () => {
		diffStore.setFiles(files, 'diff');
		diffStore.markInView('src/b.ts');

		expect(diffStore.selectedPath).toBe('src/b.ts');
		expect(diffStore.selectedFile?.path).toBe('src/b.ts');
	});

	it('is read from the server', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files }));

		await diffStore.fetchDiff();

		expect(diffStore.files.map((file) => file.path)).toEqual(['src/a.ts', 'src/b.ts']);
		expect(server.requests).toEqual([{ method: 'GET', path: '/api/diff', query: {}, body: null }]);
	});

	it('says so when it cannot be read', async () => {
		fakeServer().fail('GET /api/diff', SERVER_ERROR);

		await expect(diffStore.fetchDiff()).rejects.toThrow(`Could not take the diff: ${SERVER_ERROR}`);
	});

	it('reads as a diff until told otherwise', () => {
		expect(diffStore.mode).toBe('diff');
	});

	it('reads plain files as files', () => {
		diffStore.setFiles(files, 'files');

		expect(diffStore.mode).toBe('files');
	});

	it('reads a transcript as one', () => {
		diffStore.setFiles(files, 'transcript');

		expect(diffStore.mode).toBe('transcript');
	});

	it('takes the mode the server says the review is in', () => {
		diffStore.learn(reviewResponse({ mode: 'files' }));

		expect(diffStore.mode).toBe('files');
	});
});

describe('how a markdown file is shown', () => {
	it('is the raw text until the reader asks otherwise', () => {
		expect(diffStore.contentViewMode).toBe('raw');
	});

	it('is the way the reader picked', () => {
		diffStore.setContentViewMode('preview');

		expect(diffStore.contentViewMode).toBe('preview');
	});

	it('is remembered in this browser', () => {
		diffStore.setContentViewMode('side-by-side');

		expect(localStorage.getItem(CONTENT_VIEW_KEPT_HERE)).toBe('side-by-side');
	});

	it('stays across reviews — it is the reader\'s, not the review\'s', () => {
		diffStore.setContentViewMode('side-by-side');
		diffStore.clear();

		expect(diffStore.contentViewMode).toBe('side-by-side');
	});
});

describe('retaking the diff', () => {
	it('asks git to leave whitespace-only changes out', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse());

		await diffStore.setIgnoreWhitespace(true);

		expect(server.requestsTo('GET /api/diff')).toMatchObject([
			{ query: { ignore_whitespace: 'true' } }
		]);
		expect(diffStore.ignoreWhitespace).toBe(true);
	});

	it('keeps the files already worked through', async () => {
		fakeServer().answer('GET /api/diff', diffResponse());
		diffStore.setViewed('src/a.ts', true);

		await diffStore.setIgnoreWhitespace(true);

		// Retaking the diff must not undo a reader's progress through it
		expect(diffStore.isViewed('src/a.ts')).toBe(true);
	});

	it('drops lines revealed against hunks a round replaced', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await expansionStore.reveal('a.ts', 0, 1, 2, 0);
		expect(expansionStore.revealedCount('a.ts', 0)).toBe(2);

		await diffStore.fetchDiff();

		expect(expansionStore.revealedCount('a.ts', 0)).toBe(0);
	});

	it('drops lines revealed against hunks whitespace renumbered', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two'], total: 40 });
		server.answer('GET /api/diff', diffResponse());
		await expansionStore.reveal('a.ts', 0, 1, 2, 0);
		expect(expansionStore.revealedCount('a.ts', 0)).toBe(2);

		await diffStore.setIgnoreWhitespace(true);

		expect(expansionStore.revealedCount('a.ts', 0)).toBe(0);
	});
});

describe('how a diff is laid out', () => {
	it('is kept with the reader\'s settings, for every review', () => {
		const server = fakeServer();
		keepingSettings(server);

		diffStore.setDiffLayout('split');

		expect(diffStore.diffLayout).toBe('split');
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ diff_layout: 'split' }]);
	});

	it('stays across reviews, which are not what it belongs to', () => {
		keepingSettings(fakeServer());
		diffStore.setDiffLayout('split');

		diffStore.clear();

		expect(diffStore.diffLayout).toBe('split');
	});
});
