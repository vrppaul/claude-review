import { beforeEach, describe, it, expect } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import DiffView from '$lib/components/DiffView.svelte';
import { lineAnchor } from '$lib/anchors/line';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine, sinceRound, wholeFile } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';
import { areasWatching, scriptTheScroll, scrollTo } from '../scripted-scroll';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const changedFile = diffFile({
	path: 'src/handler.ts',
	hunks: [hunk([contextLine(1, 1, 'const x = 1;'), removedLine(2, 'const y = 2;'), addedLine(2, 'const y = 3;')])]
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
	hunks: [hunk([addedLine(1, 'export const x = 1;')])]
});

const plan = wholeFile('/tmp/plan.md', '# My Plan', 'Step one');
const readme = wholeFile('docs/readme.md', '# Hello');

describe('a diff on screen', () => {
	it('names each file', () => {
		review = openReview({ files: [changedFile] });

		const { getByText } = render(DiffView, inReview(review));

		expect(getByText('src/handler.ts')).toBeTruthy();
	});

	it('says how each file changed', () => {
		review = openReview({ files: [changedFile] });

		const { getByText } = render(DiffView, inReview(review));

		expect(getByText('modified')).toBeTruthy();
	});

	it('says nothing of a change when the files are read whole', () => {
		review = openReview({ files: [plan], facts: { mode: 'files' } });

		const { queryByText } = render(DiffView, inReview(review));

		expect(queryByText('added')).toBeNull();
	});

	it('shows what each line says', () => {
		review = openReview({ files: [changedFile] });

		const { getByTestId } = render(DiffView, inReview(review));

		// Content may be split by syntax highlighting spans, so check the container
		expect(getByTestId('diff-view').textContent).toContain('const x = 1;');
	});

	it('numbers every line, to comment on', () => {
		review = openReview({ files: [plan], facts: { mode: 'files' } });

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('line-gutter').map((gutter) => gutter.textContent?.trim())).toEqual(['1', '2']);
	});

	it('marks where the diff jumps, and says how far', () => {
		review = openReview({ files: [jumpingFile] });

		const { getByText, getByTestId } = render(DiffView, inReview(review));

		expect(getByText('@@ -30,3 +30,4 @@')).toBeTruthy();
		expect(getByTestId('hunk-gap').textContent).toContain('29 hidden lines');
	});

	it('leaves the marker out where the code runs on unbroken', () => {
		review = openReview({ files: [changedFile] });

		const { queryByTestId } = render(DiffView, inReview(review));

		// The hunk starts at line 1: nothing is hidden above it, so there is
		// no jump for a marker to announce
		expect(queryByTestId('hunk-header')).toBeNull();
	});

	it('marks no jumps in a file read whole', () => {
		review = openReview({ files: [plan], facts: { mode: 'files' } });

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('hunk-header')).toBeNull();
	});

	it('shows what a transcript message says', () => {
		review = openReview({
			files: [wholeFile('user-1', 'can you refactor auth?', 'use JWT instead')],
			facts: { mode: 'transcript' }
		});

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('diff-view').textContent).toContain('can you refactor auth?');
		expect(getByTestId('diff-view').textContent).toContain('use JWT instead');
	});

	it('says nothing of a change in a transcript', () => {
		review = openReview({ files: [wholeFile('assistant-2', 'response')], facts: { mode: 'transcript' } });

		const { queryByText } = render(DiffView, inReview(review));

		expect(queryByText('added')).toBeNull();
	});
});

describe('how a markdown file is shown', () => {
	it('can be chosen for a markdown file', () => {
		review = openReview({ files: [readme], facts: { mode: 'files' } });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('is not offered for code', () => {
		review = openReview({ files: [changedFile] });

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('content-view-toggle')).toBeNull();
	});

	it('can be chosen for a transcript message', () => {
		review = openReview({ files: [wholeFile('assistant (14:30) #1', '# Response')], facts: { mode: 'transcript' } });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('is the raw text until the reader picks another way', () => {
		review = openReview({ files: [readme], facts: { mode: 'files' } });

		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});

	it('is the preview once the reader picks it', async () => {
		review = openReview({ files: [readme], facts: { mode: 'files' } });

		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		expect(getByTestId('preview-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('says in the preview that comments are on the raw text', async () => {
		review = openReview({ files: [readme], facts: { mode: 'files' } });
		review.threads.add(newComment({ file: 'docs/readme.md', startLine: 1, body: 'Fix this heading' }));

		const { getByTestId } = render(DiffView, inReview(review));

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		const badge = getByTestId('preview-comment-badge');
		expect(badge.textContent).toContain('1 comment');
		expect(badge.textContent).toContain('switch to Raw');
	});

	it('is both side by side once the reader picks that', async () => {
		review = openReview({ files: [readme], facts: { mode: 'files' } });

		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

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
		review = openReview({ files: [changedFile] });
		review.threads.add(newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' }));

		const { getAllByText } = render(DiffView, inReview(review));

		expect(getAllByText('why was this dropped')).toHaveLength(1);
	});

	it('labels a comment on a removed line as removed', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' }));

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('comment-line-label').textContent).toBe('Removed line 2');
	});

	it('shows both sides of a replaced line as separate comments', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(newComment({ file: changedFile.path, side: 'old', startLine: 2, body: 'the old one' }));
		review.threads.add(newComment({ file: changedFile.path, side: 'new', startLine: 2, body: 'the new one' }));

		const { getAllByText } = render(DiffView, inReview(review));

		expect(getAllByText('the old one')).toHaveLength(1);
		expect(getAllByText('the new one')).toHaveLength(1);
	});
});

describe('files with no lines to show', () => {
	const binaryFile = diffFile({ path: 'docs/logo.png', status: 'added', unshown: 'binary' });

	const modeOnlyFile = diffFile({
		path: 'scripts/run.sh',
		old_mode: '100644',
		new_mode: '100755'
	});

	it('explains why a binary file shows nothing', () => {
		review = openReview({ files: [binaryFile] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('empty-file-note').textContent).toContain('Binary file');
	});

	it('says a file too large to show is too large, and how large that is, rather than calling it binary', () => {
		review = openReview({ files: [diffFile({ path: 'generated.log', status: 'added', unshown: 'too_large' })] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('empty-file-note').textContent?.trim()).toBe('Too large to show (over 4 MB)');
	});

	it('shows a permission change that touched no line', () => {
		review = openReview({ files: [modeOnlyFile] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('mode-change-note').textContent).toContain('100644 → 100755');
	});

	it('keeps a permission change in sight when the diff reads across two columns', async () => {
		keepingSettings(fakeServer());
		review = openReview({ files: [{ ...changedFile, old_mode: '100644', new_mode: '100755' }] });
		await review.settings.change({ diff_layout: 'split' });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('split-view')).toBeTruthy();
		expect(getByTestId('mode-change-note').textContent).toContain('100644 → 100755');
	});

	it('draws a file with no lines in one column, though the reader reads changes across two', async () => {
		keepingSettings(fakeServer());
		review = openReview({ files: [binaryFile] });
		await review.settings.change({ diff_layout: 'split' });

		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('split-view')).toBeNull();
		expect(getByTestId('raw-view')).toBeTruthy();
	});

	it('says a file turned into a link as a change of what it is, not of its permissions', () => {
		review = openReview({ files: [{ ...changedFile, old_mode: '100644', new_mode: '120000' }] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('mode-change-note').textContent).toContain('Type changed: file → link');
		expect(getByTestId('mode-change-note').textContent).not.toContain('Permission');
	});

	it('says a link turned back into a file the same way', () => {
		review = openReview({ files: [{ ...changedFile, old_mode: '120000', new_mode: '100755' }] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('mode-change-note').textContent).toContain('Type changed: link → file');
	});

	it('names a moved file by where it was as well as where it is', () => {
		review = openReview({ files: [{ ...changedFile, status: 'renamed', old_path: 'src/old_handler.ts' }] });

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('file-heading').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'src/old_handler.ts → src/handler.ts'
		);
	});

	it('does not claim an empty panel for a file that has hunks', () => {
		review = openReview({ files: [changedFile] });

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('empty-file-note')).toBeNull();
		expect(queryByTestId('mode-change-note')).toBeNull();
	});
});

describe('a comment on a file the diff no longer has', () => {
	// The agent put the file back as it was, and the diff was taken again without it
	const onTheRevertedFile = {
		...newComment({ file: 'src/reverted.ts', body: 'why this change' }),
		anchor: { ...lineAnchor('src/reverted.ts', 'new', 1, 1, ['const z = 1;']), outdated: true }
	};

	it('is drawn above the files, whole, rather than nowhere', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(onTheRevertedFile);
		review.threads.add(newComment({ file: changedFile.path, startLine: 2, body: 'on a line still there' }));

		const { getByTestId } = render(DiffView, inReview(review));

		const above = getByTestId('unplaced-threads');
		expect(above.textContent).toContain('1 comment on src/reverted.ts, a file no longer in the diff');
		expect(within(above).getAllByTestId('comment-thread')).toHaveLength(1);
		expect(above.textContent).toContain('why this change');
		expect(above.textContent).not.toContain('on a line still there');
		expect(above.compareDocumentPosition(getByTestId('file-section'))).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
	});

	it('is drawn under the name of its file, each file apart', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(onTheRevertedFile);
		review.threads.add(newComment({ file: 'src/also-reverted.ts', body: 'and this one' }));
		review.threads.add(newComment({ file: 'src/reverted.ts', startLine: 4, body: 'and further down' }));

		const { getAllByTestId } = render(DiffView, inReview(review));

		const [first, second] = getAllByTestId('unplaced-threads');
		expect(first.textContent).toContain('2 comments on src/reverted.ts, a file no longer in the diff');
		expect(within(first).getAllByTestId('comment-thread')).toHaveLength(2);
		expect(second.textContent).toContain('1 comment on src/also-reverted.ts, a file no longer in the diff');
		expect(second.textContent).toContain('and this one');
	});

	it('is drawn when the diff has no file left at all', () => {
		review = openReview({ files: [] });
		review.threads.add(onTheRevertedFile);

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('no-changes')).toBeTruthy();
		expect(within(getByTestId('unplaced-threads')).getByText('why this change')).toBeTruthy();
	});

	it('can be deleted where it is drawn', async () => {
		const user = userEvent.setup();
		review = openReview({ files: [changedFile] });
		review.threads.add(onTheRevertedFile);
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		await user.click(within(getByTestId('unplaced-threads')).getByTestId('delete-comment'));
		await user.click(getByTestId('confirm-go-ahead'));

		expect(review.threads.all).toEqual([]);
		expect(queryByTestId('unplaced-threads')).toBeNull();
	});

	it('is left to the notice above the diff under a narrower base, which names every thread it cannot draw', async () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(onTheRevertedFile);
		fakeServer().answer('GET /api/diff', diffResponse({ files: [changedFile], base: sinceRound(1) }));
		await review.diff.setBase('round:1');

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('unplaced-threads')).toBeNull();
	});
});

describe('editing a comment', () => {
	it('keeps the removed wording when the comment is reopened for editing', async () => {
		const user = userEvent.setup();
		review = openReview({ files: [changedFile] });
		review.threads.add(newComment({ file: 'src/handler.ts', side: 'old', startLine: 2, body: 'why was this dropped' }));

		const { getByText, getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('edit-comment'));

		expect(getByTestId('comment-input')).toBeTruthy();
		expect(getByText('Removed line 2')).toBeTruthy();
	});
});

describe('the diff as one stream', () => {
	it('shows every file at once instead of one at a time', () => {
		review = openReview({ files: [changedFile, secondFile] });

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('file-section')).toHaveLength(2);
	});

	it('keeps the files in the order the diff gave them', () => {
		review = openReview({ files: [changedFile, secondFile] });

		const { getAllByTestId } = render(DiffView, inReview(review));
		const paths = getAllByTestId('file-section').map((section) => section.dataset.path);

		expect(paths).toEqual(['src/handler.ts', 'src/other.ts']);
	});

	it('lets a comment be left on any file without switching to it first', async () => {
		const user = userEvent.setup();
		review = openReview({ files: [changedFile, secondFile] });

		const { getAllByTestId, getByTestId } = render(DiffView, inReview(review));
		const [, second] = getAllByTestId('file-section');

		await user.click(within(second).getByRole('button', { name: 'Comment on line 1' }));
		await user.click(document.body);

		expect(getByTestId('comment-input')).toBeTruthy();
	});
});

describe('showing how a comment is meant', () => {
	it('marks a blocker as one', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(
			newComment({
				file: 'src/handler.ts',
				startLine: 2,
				body: 'This drops the lock',
				severity: 'blocker'
			})
		);

		const { getByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('comment-severity').textContent).toBe('blocker');
	});

	it('says nothing on an ordinary note', () => {
		review = openReview({ files: [changedFile] });
		review.threads.add(newComment({ file: 'src/handler.ts', startLine: 2, body: 'Reads well' }));

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('comment-severity')).toBeNull();
	});
});

// The scroll is scripted here; the reader kept in the file they read across a
// real retake is held by tests/e2e/test_reading_place.py
describe('the file being read', () => {
	beforeEach(() => {
		scriptTheScroll();
	});

	it('is followed into a file that a retake put where another was', async () => {
		review = openReview({ files: [changedFile, jumpingFile] });
		const { getAllByTestId } = render(DiffView, inReview(review));
		fakeServer().answer('GET /api/diff', diffResponse({ files: [changedFile, secondFile] }));
		await review.diff.take();
		flushSync();

		const [, arrived] = getAllByTestId('file-section');
		expect(arrived.dataset.path).toBe(secondFile.path);

		scrollTo(arrived);

		expect(review.sections.fileInView).toBe(secondFile.path);
	});

	it('is watched for coming near within the area the files scroll in, not within the page', () => {
		review = openReview({ files: [changedFile] });
		const { getByTestId } = render(DiffView, inReview(review));
		flushSync();

		expect(new Set(areasWatching(getByTestId('file-section')))).toEqual(new Set([getByTestId('diff-view')]));
	});
});
