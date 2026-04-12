import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
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
});
