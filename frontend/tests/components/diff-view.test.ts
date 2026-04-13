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
		diffStore.clear();
		commentStore.clear();
	});

	it('shows file path in header', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView, { props: { file: diffFile } });

		expect(getByText('src/handler.ts')).toBeTruthy();
	});

	it('shows file status badge in diff mode', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView, { props: { file: diffFile } });

		expect(getByText('modified')).toBeTruthy();
	});

	it('hides file status badge in files mode', () => {
		diffStore.setFiles([textFile], 'files');

		const { queryByText } = render(DiffView, { props: { file: textFile } });

		expect(queryByText('added')).toBeNull();
	});

	it('renders line content', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByTestId } = render(DiffView, { props: { file: diffFile } });

		// Content may be split by syntax highlighting spans, so check the container
		expect(getByTestId('diff-view').textContent).toContain('const x = 1;');
	});

	it('renders line gutters for commenting', () => {
		diffStore.setFiles([textFile], 'files');

		const { getAllByTestId } = render(DiffView, { props: { file: textFile } });

		const gutters = getAllByTestId('line-gutter');
		expect(gutters).toHaveLength(2);
		expect(gutters[0].textContent?.trim()).toBe('1');
		expect(gutters[1].textContent?.trim()).toBe('2');
	});

	it('shows hunk header in diff mode', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { getByText } = render(DiffView, { props: { file: diffFile } });

		expect(getByText('@@ -1,3 +1,4 @@')).toBeTruthy();
	});

	it('hides hunk header in files mode', () => {
		diffStore.setFiles([textFile], 'files');

		const { queryByText } = render(DiffView, { props: { file: textFile } });

		// Empty header should not render
		expect(queryByText('@@ ')).toBeNull();
	});

	it('renders transcript message content', () => {
		const transcriptFile: DiffFile = {
			path: 'user-1',
			status: 'added',
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

		const { getByTestId } = render(DiffView, { props: { file: transcriptFile } });

		expect(getByTestId('diff-view').textContent).toContain('can you refactor auth?');
		expect(getByTestId('diff-view').textContent).toContain('use JWT instead');
	});

	it('shows content view toggle for markdown files', () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
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

		const { getByTestId } = render(DiffView, { props: { file: mdFile } });

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('hides content view toggle for non-markdown files', () => {
		diffStore.setFiles([diffFile], 'diff');

		const { queryByTestId } = render(DiffView, { props: { file: diffFile } });

		expect(queryByTestId('content-view-toggle')).toBeNull();
	});

	it('shows content view toggle in transcript mode', () => {
		const transcriptFile: DiffFile = {
			path: 'assistant (14:30) #1',
			status: 'added',
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

		const { getByTestId } = render(DiffView, { props: { file: transcriptFile } });

		expect(getByTestId('content-view-toggle')).toBeTruthy();
	});

	it('switches to preview mode when toggle is clicked', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
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

		const { getByTestId, queryByTestId } = render(DiffView, { props: { file: mdFile } });

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		expect(getByTestId('preview-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('preview mode shows comment badge when comments exist', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
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
		commentStore.add('docs/readme.md', 1, 1, 'Fix this heading');

		const { getByTestId } = render(DiffView, { props: { file: mdFile } });

		await userEvent.setup().click(getByTestId('view-mode-preview'));

		const badge = getByTestId('preview-comment-badge');
		expect(badge.textContent).toContain('1 comment');
		expect(badge.textContent).toContain('switch to Raw');
	});

	it('shows raw view by default for markdown files', () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
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

		const { getByTestId, queryByTestId } = render(DiffView, { props: { file: mdFile } });

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('preview-view')).toBeNull();
	});

	it('switches to side-by-side mode when toggle is clicked', async () => {
		const mdFile: DiffFile = {
			path: 'docs/readme.md',
			status: 'added',
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

		const { getByTestId, queryByTestId } = render(DiffView, { props: { file: mdFile } });

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

		const { queryByText } = render(DiffView, { props: { file: transcriptFile } });

		expect(queryByText('added')).toBeNull();
	});
});
