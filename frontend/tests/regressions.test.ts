import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { isTypingTarget } from '$lib/utils/keyboard';
import type { DiffFile } from '$lib/types';
import { newComment } from './new-comment';

const file: DiffFile = {
	path: 'src/app.ts',
	status: 'modified',
	hunks: [
		{
			header: '@@ -1,3 +1,3 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'const a = 1;' },
				{ type: 'delete', old_no: 2, new_no: null, content: 'const b = 2;' },
				{ type: 'add', old_no: null, new_no: 2, content: 'const b = 3;' }
			]
		}
	],
	is_binary: false,
	old_mode: null,
	new_mode: null
};

describe('a comment on an unchanged line in the split layout', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		localStorage.clear();
		diffStore.setFiles([file], 'diff');
	});

	it('is shown once, not once per column', () => {
		// An unchanged line is the same line on both sides of the row
		commentStore.add(newComment({ file: 'src/app.ts', side: 'new', startLine: 1, endLine: 1, body: 'name this' }));
		diffStore.setDiffLayout('split');

		const { getAllByText } = render(FileSection, { props: { file } });

		expect(getAllByText('name this')).toHaveLength(1);
	});

	it('still shows a comment on each side of a replacement', () => {
		commentStore.add(newComment({ file: 'src/app.ts', side: 'old', startLine: 2, endLine: 2, body: 'why gone' }));
		commentStore.add(newComment({ file: 'src/app.ts', side: 'new', startLine: 2, endLine: 2, body: 'why this' }));
		diffStore.setDiffLayout('split');

		const { getAllByText } = render(FileSection, { props: { file } });

		expect(getAllByText('why gone')).toHaveLength(1);
		expect(getAllByText('why this')).toHaveLength(1);
	});
});

describe('which keys belong to the review', () => {
	it('leaves letters alone while a comment is being typed', () => {
		const textarea = document.createElement('textarea');
		expect(isTypingTarget(textarea)).toBe(true);
	});

	it('keeps working after a checkbox has been clicked', () => {
		// Focus parks on the hidden input behind "Viewed"; that is not typing
		const checkbox = document.createElement('input');
		checkbox.type = 'checkbox';

		expect(isTypingTarget(checkbox)).toBe(false);
	});

	it('leaves the filter box to itself', () => {
		const search = document.createElement('input');
		search.type = 'search';

		expect(isTypingTarget(search)).toBe(true);
	});
});

describe('comment ids after a draft comes back', () => {
	beforeEach(() => {
		localStorage.clear();
		commentStore.clear();
	});

	it('never hands out an id a restored comment already has', () => {
		commentStore.restore('repo: uncommitted changes');
		const first = commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 1, endLine: 1, body: 'one' }));
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 2, endLine: 2, body: 'two' }));
		commentStore.remove(first);

		commentStore.clear();
		commentStore.restore('repo: uncommitted changes');
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 3, endLine: 3, body: 'three' }));

		const ids = commentStore.comments.map((c) => c.id);
		expect(new Set(ids).size).toBe(ids.length);
	});
});

describe('stepping through comments', () => {
	beforeEach(() => {
		localStorage.clear();
		commentStore.clear();
	});

	it('keeps one position, so two controls cannot disagree', () => {
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 1, endLine: 1, body: 'one' }));
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 2, endLine: 2, body: 'two' }));

		expect(commentStore.step(1)?.body).toBe('one');
		expect(commentStore.step(1)?.body).toBe('two');
		expect(commentStore.step(-1)?.body).toBe('one');
	});

	it('wraps around rather than stopping at the end', () => {
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 1, endLine: 1, body: 'one' }));

		expect(commentStore.step(1)?.body).toBe('one');
		expect(commentStore.step(1)?.body).toBe('one');
	});

	it('has nothing to step to when there are no comments', () => {
		expect(commentStore.step(1)).toBeUndefined();
	});
});

describe('retaking the diff', () => {
	it('drops lines revealed against the hunks it replaces', async () => {
		const { expansionStore } = await import('$lib/stores/expansions.svelte');
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ files: [], mode: 'diff', title: 'repo' })
			})
		);
		diffStore.clear();
		await expansionStore.reveal('a.ts', 0, 1, 2).catch(() => {});

		await diffStore.setIgnoreWhitespace(true);

		expect(expansionStore.revealedCount('a.ts', 0)).toBe(0);
		vi.unstubAllGlobals();
	});
});
