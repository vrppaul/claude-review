import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import type { DiffFile } from '$lib/types';

const diffFile: DiffFile = {
	path: 'src/handler.ts',
	status: 'modified',
	is_binary: false,
	old_mode: null,
	new_mode: null,
	hunks: [
		{
			header: '@@ -1,3 +1,4 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'const x = 1;' },
				{ type: 'delete', old_no: 2, new_no: null, content: 'const y = 2;' },
				{ type: 'add', old_no: null, new_no: 2, content: 'const y = 3;' }
			]
		}
	]
};

const textFile: DiffFile = {
	path: '/tmp/plan.md',
	status: 'added',
	is_binary: false,
	old_mode: null,
	new_mode: null,
	hunks: [
		{
			header: '',
			old_start: 0,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: null, new_no: 1, content: '# My Plan' },
				{ type: 'context', old_no: null, new_no: 2, content: 'Step one' }
			]
		}
	]
};

describe('DiffView', () => {
	beforeEach(() => {
		// The reader's view choices outlive a review now, so a test about
		// defaults has to start without one stored
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	it('shows file path in header', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView);

		expect(getByText('src/handler.ts')).toBeTruthy();
	});

	it('shows file status badge in diff mode', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView);

		expect(getByText('modified')).toBeTruthy();
	});

	it('hides file status badge in files mode', () => {
		diffStore.setFiles([textFile], 'files');

		const { queryByText } = render(DiffView);

		expect(queryByText('added')).toBeNull();
	});

	it('renders line content', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByTestId } = render(DiffView);

		// Content may be split by syntax highlighting spans, so check the container
		expect(getByTestId('diff-view').textContent).toContain('const x = 1;');
	});

	it('renders line gutters for commenting', () => {
		diffStore.setFiles([textFile], 'files');

		const { getAllByTestId } = render(DiffView);

		const gutters = getAllByTestId('line-gutter');
		expect(gutters).toHaveLength(2);
		expect(gutters[0].textContent?.trim()).toBe('1');
		expect(gutters[1].textContent?.trim()).toBe('2');
	});

	it('shows hunk header in diff mode', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView);

		expect(getByText('@@ -1,3 +1,4 @@')).toBeTruthy();
	});

	it('hides hunk header in files mode', () => {
		diffStore.setFiles([textFile], 'files');

		const { queryByText } = render(DiffView);

		// Empty header should not render
		expect(queryByText('@@ ')).toBeNull();
	});

	it('renders transcript message content', () => {
		const transcriptFile: DiffFile = {
			path: 'user-1',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [
						{ type: 'context', old_no: null, new_no: 1, content: 'can you refactor auth?' },
						{ type: 'context', old_no: null, new_no: 2, content: 'use JWT instead' }
					]
				}
			]
		};
		diffStore.setFiles([transcriptFile], 'transcript');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('diff-view').textContent).toContain('can you refactor auth?');
		expect(getByTestId('diff-view').textContent).toContain('use JWT instead');
	});

	it('shows content view toggle for markdown files', () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Hello' }]
				}
			]
		};
		diffStore.setFiles([mdFile], 'files');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('hides content view toggle for non-markdown files', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('content-view-toggle')).toBeNull();
	});

	it('shows content view toggle in transcript mode', () => {
		const transcriptFile: DiffFile = {
			path: 'assistant (14:30) #1',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Response' }]
				}
			]
		};
		diffStore.setFiles([transcriptFile], 'transcript');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('switches to preview mode when toggle is clicked', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Hello' }]
				}
			]
		};
		diffStore.setFiles([mdFile], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		expect(getByTestId('preview-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('preview mode shows comment badge when comments exist', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Hello' }]
				}
			]
		};
		diffStore.setFiles([mdFile], 'files');
		commentStore.add('docs/readme.md', 'new', 1, 1, 'Fix this heading');

		const { getByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		const badge = getByTestId('preview-comment-badge');
		expect(badge.textContent).toContain('1 comment');
		expect(badge.textContent).toContain('switch to Raw');
	});

	it('shows raw view by default for markdown files', () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Hello' }]
				}
			]
		};
		diffStore.setFiles([mdFile], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});

	it('switches to side-by-side mode when toggle is clicked', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: '# Hello' }]
				}
			]
		};
		diffStore.setFiles([mdFile], 'files');

		const { getByTestId, queryByTestId } = render(DiffView);

		await userEvent.setup().click(getByTestId('view-mode-side-by-side'));

		expect(getByTestId('side-by-side-view')).toBeTruthy();
		// raw-view is present as the left pane inside side-by-side
		expect(getByTestId('raw-view')).toBeTruthy();
		expect(getByTestId('markdown-content')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});

	it('hides status badge in transcript mode', () => {
		const transcriptFile: DiffFile = {
			path: 'assistant-2',
			status: 'added',
			is_binary: false,
			old_mode: null,
			new_mode: null,
			hunks: [
				{
					header: '',
					old_start: 0,
					new_start: 1,
					lines: [{ type: 'context', old_no: null, new_no: 1, content: 'response' }]
				}
			]
		};
		diffStore.setFiles([transcriptFile], 'transcript');

		const { queryByText } = render(DiffView);

		expect(queryByText('added')).toBeNull();
	});
});

describe('comment anchoring across diff sides', () => {
	beforeEach(() => {
		// The reader's view choices outlive a review now, so a test about
		// defaults has to start without one stored
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	it('shows a comment on a removed line only once', () => {
		// The fixture replaces line 2, so old line 2 and new line 2 both exist.
		diffStore.setFiles([diffFile], 'diff');
		commentStore.add('src/handler.ts', 'old', 2, 2, 'why was this dropped');

		const { getAllByText } = render(DiffView);

		expect(getAllByText('why was this dropped')).toHaveLength(1);
	});

	it('labels a comment on a removed line as removed', () => {
		diffStore.setFiles([diffFile], 'diff');
		commentStore.add('src/handler.ts', 'old', 2, 2, 'why was this dropped');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('comment-line-label').textContent).toBe('Removed line 2');
	});

	it('shows both sides of a replaced line as separate comments', () => {
		diffStore.setFiles([diffFile], 'diff');
		commentStore.add('src/handler.ts', 'old', 2, 2, 'the old one');
		commentStore.add('src/handler.ts', 'new', 2, 2, 'the new one');

		const { getAllByText } = render(DiffView);

		expect(getAllByText('the old one')).toHaveLength(1);
		expect(getAllByText('the new one')).toHaveLength(1);
	});
});

describe('files with no lines to show', () => {
	beforeEach(() => {
		// The reader's view choices outlive a review now, so a test about
		// defaults has to start without one stored
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	const binaryFile: DiffFile = {
		path: 'docs/logo.png',
		status: 'added',
		hunks: [],
		is_binary: true,
		old_mode: null,
		new_mode: null
	};

	const modeOnlyFile: DiffFile = {
		path: 'scripts/run.sh',
		status: 'modified',
		hunks: [],
		is_binary: false,
		old_mode: '100644',
		new_mode: '100755'
	};

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

	it('does not claim an empty panel for a file that has hunks', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('empty-file-note')).toBeNull();
		expect(queryByTestId('mode-change-note')).toBeNull();
	});
});

describe('editing a comment', () => {
	beforeEach(() => {
		// The reader's view choices outlive a review now, so a test about
		// defaults has to start without one stored
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	it('keeps the removed wording when the comment is reopened for editing', async () => {
		const user = userEvent.setup();
		diffStore.setFiles([diffFile], 'diff');
		commentStore.add('src/handler.ts', 'old', 2, 2, 'why was this dropped');

		const { getByText, getByTestId } = render(DiffView);
		await user.click(getByText('Edit'));

		expect(getByTestId('comment-input')).toBeTruthy();
		expect(getByText('Removed line 2')).toBeTruthy();
	});
});

describe('the diff as one stream', () => {
	beforeEach(() => {
		// The reader's view choices outlive a review now, so a test about
		// defaults has to start without one stored
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	const second: DiffFile = {
		path: 'src/other.ts',
		status: 'added',
		hunks: [
			{
				header: '@@ -0,0 +1,1 @@',
				old_start: 0,
				new_start: 1,
				lines: [{ type: 'add', old_no: null, new_no: 1, content: 'export const x = 1;' }]
			}
		],
		is_binary: false,
		old_mode: null,
		new_mode: null
	};

	it('shows every file at once instead of one at a time', () => {
		diffStore.setFiles([diffFile, second], 'diff');

		const { getAllByTestId } = render(DiffView);

		expect(getAllByTestId('file-section')).toHaveLength(2);
	});

	it('keeps the files in the order the diff gave them', () => {
		diffStore.setFiles([diffFile, second], 'diff');

		const { getAllByTestId } = render(DiffView);
		const paths = getAllByTestId('file-section').map((el) => el.dataset.path);

		expect(paths).toEqual(['src/handler.ts', 'src/other.ts']);
	});

	it('lets a comment be left on any file without switching to it first', async () => {
		const user = userEvent.setup();
		diffStore.setFiles([diffFile, second], 'diff');

		const { getAllByTestId, getByTestId } = render(DiffView);
		const secondSection = getAllByTestId('file-section')[1];
		const gutter = secondSection.querySelector('[data-testid="line-gutter"]')!;

		await user.click(gutter);
		await user.click(document.body);

		expect(getByTestId('comment-input')).toBeTruthy();
	});
});

describe('showing how a comment is meant', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		diffStore.setFiles([diffFile], 'diff');
	});

	it('marks a blocker as one', () => {
		commentStore.add('src/handler.ts', 'new', 2, 2, 'This drops the lock', 'blocker');

		const { getByTestId } = render(DiffView);

		expect(getByTestId('comment-severity').textContent).toBe('blocker');
	});

	it('says nothing on an ordinary note', () => {
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Reads well');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('comment-severity')).toBeNull();
	});
});
