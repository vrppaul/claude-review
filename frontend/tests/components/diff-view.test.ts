import { describe, it, expect } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { addedLine, contextLine, diffFile, hunk, removedLine, wholeFile } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';

const changedFile = diffFile({
	path: 'src/handler.ts',
	hunks: [
		hunk([
			contextLine(1, 1, 'const x = 1;'),
			removedLine(2, 'const y = 2;'),
			addedLine(2, 'const y = 3;')
		])
	]
});

/** The same change, further down a file, with lines hidden above it. */
const jumpingFile = diffFile({
	path: 'src/later.ts',
	hunks: [
		hunk([contextLine(30, 30, 'const x = 1;'), addedLine(31, 'const y = 3;')], {
			header: '@@ -30,3 +30,4 @@',
			old_start: 30,
			new_start: 30
		})
	]
});

const secondFile = diffFile({
	path: 'src/other.ts',
	status: 'added',
	hunks: [hunk([addedLine(1, 'export const x = 1;')], { old_start: 0 })]
});

const plan = wholeFile('/tmp/plan.md', '# My Plan', 'Step one');
const readme = wholeFile('docs/readme.md', '# Hello');

describe('a diff on screen', () => {
	it('names each file', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { getByText } = render(DiffView);

		expect(getByText('src/handler.ts')).toBeTruthy();
	});

	it('says how each file changed', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { getByText } = render(DiffView);

		expect(getByText('modified')).toBeTruthy();
	});

	it('says nothing of a change when the files are read whole', () => {
		diffStore.setFiles([plan], 'files');

		const { queryByText } = render(DiffView);

		expect(queryByText('added')).toBeNull();
	});

	it('shows what each line says', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { getByTestId } = render(DiffView);

		// Content may be split by syntax highlighting spans, so check the container
		expect(getByTestId('diff-view').textContent).toContain('const x = 1;');
	});

	it('numbers every line, to comment on', () => {
		diffStore.setFiles([plan], 'files');

		const { getAllByTestId } = render(DiffView);

		expect(getAllByTestId('line-gutter').map((gutter) => gutter.textContent?.trim())).toEqual([
			'1',
			'2'
		]);
	});

	it('marks where the diff jumps, and says how far', () => {
		diffStore.setFiles([jumpingFile], 'diff');

		const { getByText, getByTestId } = render(DiffView);

		expect(getByText('@@ -30,3 +30,4 @@')).toBeTruthy();
		expect(getByTestId('expand-context').textContent).toContain('29 hidden lines');
	});

	it('leaves the marker out where the code runs on unbroken', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { queryByTestId } = render(DiffView);

		// The hunk starts at line 1: nothing is hidden above it, so there is
		// no jump for a marker to announce
		expect(queryByTestId('hunk-header')).toBeNull();
	});

	it('marks no jumps in a file read whole', () => {
		diffStore.setFiles([plan], 'files');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('hunk-header')).toBeNull();
	});

	it('shows what a transcript message says', () => {
		diffStore.setFiles(
			[wholeFile('user-1', 'can you refactor auth?', 'use JWT instead')],
			'transcript'
		);

		const { getByTestId } = render(DiffView);

		expect(getByTestId('diff-view').textContent).toContain('can you refactor auth?');
		expect(getByTestId('diff-view').textContent).toContain('use JWT instead');
	});

	it('says nothing of a change in a transcript', () => {
		diffStore.setFiles([wholeFile('assistant-2', 'response')], 'transcript');

		const { queryByText } = render(DiffView);

		expect(queryByText('added')).toBeNull();
	});
});

describe('how a markdown file is shown', () => {
	it('can be chosen for a markdown file', () => {
		diffStore.setFiles([readme], 'files');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('is not offered for code', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('content-view-toggle')).toBeNull();
	});

	it('can be chosen for a transcript message', () => {
		diffStore.setFiles([wholeFile('assistant (14:30) #1', '# Response')], 'transcript');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('is the raw text until the reader picks another way', () => {
		diffStore.setFiles([readme], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});

	it('is the preview once the reader picks it', async () => {
		diffStore.setFiles([readme], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		expect(getByTestId('preview-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('says in the preview that comments are on the raw text', async () => {
		diffStore.setFiles([readme], 'files');
		commentStore.add(newComment({ file: 'docs/readme.md', startLine: 1, body: 'Fix this heading' }));

		const { getByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		const badge = getByTestId('preview-comment-badge');
		expect(badge.textContent).toContain('1 comment');
		expect(badge.textContent).toContain('switch to Raw');
	});

	it('is both side by side once the reader picks that', async () => {
		diffStore.setFiles([readme], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-side-by-side'));

		expect(getByTestId('side-by-side-view')).toBeTruthy();
		// raw-view is present as the left pane inside side-by-side
		expect(getByTestId('raw-view')).toBeTruthy();
		expect(getByTestId('markdown-content')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});
});

describe('comment anchoring across diff sides', () => {
	it('shows a comment on a removed line only once', () => {
		// The fixture replaces line 2, so old line 2 and new line 2 both exist.
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(
			newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' })
		);

		const { getAllByText } = render(DiffView);

		expect(getAllByText('why was this dropped')).toHaveLength(1);
	});

	it('labels a comment on a removed line as removed', () => {
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(
			newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' })
		);

		const { getByTestId } = render(DiffView);

		expect(getByTestId('comment-line-label').textContent).toBe('Removed line 2');
	});

	it('shows both sides of a replaced line as separate comments', () => {
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(
			newComment({ file: changedFile.path, side: 'old', startLine: 2, body: 'the old one' })
		);
		commentStore.add(
			newComment({ file: changedFile.path, side: 'new', startLine: 2, body: 'the new one' })
		);

		const { getAllByText } = render(DiffView);

		expect(getAllByText('the old one')).toHaveLength(1);
		expect(getAllByText('the new one')).toHaveLength(1);
	});
});

describe('files with no lines to show', () => {
	const binaryFile = diffFile({ path: 'docs/logo.png', status: 'added', is_binary: true });

	const modeOnlyFile = diffFile({
		path: 'scripts/run.sh',
		old_mode: '100644',
		new_mode: '100755'
	});

	it('explains why a binary file shows nothing', () => {
		diffStore.setFiles([binaryFile], 'diff');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('empty-file-note').textContent).toContain('Binary file');
	});

	it('shows a permission change that touched no line', () => {
		diffStore.setFiles([modeOnlyFile], 'diff');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('mode-change-note').textContent).toContain('100644 → 100755');
	});

	it('keeps a permission change in sight when the diff reads across two columns', () => {
		keepingSettings(fakeServer());
		diffStore.setDiffLayout('split');
		diffStore.setFiles([{ ...changedFile, old_mode: '100644', new_mode: '100755' }], 'diff');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('split-view')).toBeTruthy();
		expect(getByTestId('mode-change-note').textContent).toContain('100644 → 100755');
	});

	it('does not claim an empty panel for a file that has hunks', () => {
		diffStore.setFiles([changedFile], 'diff');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('empty-file-note')).toBeNull();
		expect(queryByTestId('mode-change-note')).toBeNull();
	});
});

describe('editing a comment', () => {
	it('keeps the removed wording when the comment is reopened for editing', async () => {
		const user = userEvent.setup();
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(
			newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' })
		);

		const { getByText, getByTestId } = render(DiffView);
		await user.click(getByTestId('edit-comment'));

		expect(getByTestId('comment-input')).toBeTruthy();
		expect(getByText('Removed line 2')).toBeTruthy();
	});
});

describe('the diff as one stream', () => {
	it('shows every file at once instead of one at a time', () => {
		diffStore.setFiles([changedFile, secondFile], 'diff');

		const { getAllByTestId } = render(DiffView);

		expect(getAllByTestId('file-section')).toHaveLength(2);
	});

	it('keeps the files in the order the diff gave them', () => {
		diffStore.setFiles([changedFile, secondFile], 'diff');

		const { getAllByTestId } = render(DiffView);
		const paths = getAllByTestId('file-section').map((section) => section.dataset.path);

		expect(paths).toEqual(['src/handler.ts', 'src/other.ts']);
	});

	it('lets a comment be left on any file without switching to it first', async () => {
		const user = userEvent.setup();
		diffStore.setFiles([changedFile, secondFile], 'diff');

		const { getAllByTestId, getByTestId } = render(DiffView);
		const [, second] = getAllByTestId('file-section');

		await user.click(within(second).getAllByTestId('line-gutter')[0]);
		await user.click(document.body);

		expect(getByTestId('comment-input')).toBeTruthy();
	});
});

describe('showing how a comment is meant', () => {
	it('marks a blocker as one', () => {
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(
			newComment({
				file: 'src/handler.ts',
				startLine: 2,
				body: 'This drops the lock',
				severity: 'blocker'
			})
		);

		const { getByTestId } = render(DiffView);

		expect(getByTestId('comment-severity').textContent).toBe('blocker');
	});

	it('says nothing on an ordinary note', () => {
		diffStore.setFiles([changedFile], 'diff');
		commentStore.add(newComment({ file: 'src/handler.ts', startLine: 2, body: 'Reads well' }));

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('comment-severity')).toBeNull();
	});
});
