import { describe, it, expect, beforeEach, vi } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';

describe('commentStore', () => {
	beforeEach(() => {
		commentStore.clear();
	});

	it('starts with zero comments', () => {
		expect(commentStore.count).toBe(0);
		expect(commentStore.comments).toEqual([]);
	});

	it('adds a comment with generated id', () => {
		const id = commentStore.add('file.ts', 10, 10, 'fix this');

		expect(id).toBeTruthy();
		expect(commentStore.count).toBe(1);
		expect(commentStore.comments[0]).toMatchObject({
			file: 'file.ts',
			start_line: 10,
			end_line: 10,
			body: 'fix this'
		});
	});

	it('adds multi-line comment', () => {
		commentStore.add('file.ts', 10, 15, 'refactor this block');

		expect(commentStore.comments[0].start_line).toBe(10);
		expect(commentStore.comments[0].end_line).toBe(15);
	});

	it('updates a comment body', () => {
		const id = commentStore.add('file.ts', 1, 1, 'original');
		commentStore.update(id, 'updated');

		expect(commentStore.comments[0].body).toBe('updated');
	});

	it('removes a comment', () => {
		const id = commentStore.add('file.ts', 1, 1, 'to delete');
		commentStore.remove(id);

		expect(commentStore.count).toBe(0);
	});

	it('filters comments by file', () => {
		commentStore.add('a.ts', 1, 1, 'comment A');
		commentStore.add('b.ts', 1, 1, 'comment B');
		commentStore.add('a.ts', 5, 5, 'comment A2');

		expect(commentStore.getForFile('a.ts')).toHaveLength(2);
		expect(commentStore.getForFile('b.ts')).toHaveLength(1);
		expect(commentStore.getForFile('c.ts')).toHaveLength(0);
	});

	it('getForLine returns comments anchored at their end line only', () => {
		commentStore.add('file.ts', 10, 15, 'range comment');
		commentStore.add('file.ts', 20, 20, 'single line');

		// Range comment only renders at end_line (15), not at start or middle
		expect(commentStore.getForLine('file.ts', 10)).toHaveLength(0);
		expect(commentStore.getForLine('file.ts', 12)).toHaveLength(0);
		expect(commentStore.getForLine('file.ts', 15)).toHaveLength(1);
		// Outside range
		expect(commentStore.getForLine('file.ts', 16)).toHaveLength(0);
		// Single line comment at line 20
		expect(commentStore.getForLine('file.ts', 20)).toHaveLength(1);
	});

	it('clear resets everything', () => {
		commentStore.add('a.ts', 1, 1, 'x');
		commentStore.add('b.ts', 2, 2, 'y');
		commentStore.clear();

		expect(commentStore.count).toBe(0);
		expect(commentStore.submitted).toBe(false);
	});

	describe('submit', () => {
		it('sends correct payload and sets submitted', async () => {
			vi.stubGlobal(
				'fetch',
				vi.fn().mockResolvedValue({
					ok: true,
					json: () => Promise.resolve({ markdown: '## Comments', comment_count: 1 })
				})
			);

			commentStore.add('file.ts', 10, 10, 'fix this');
			const result = await commentStore.submit();

			expect(fetch).toHaveBeenCalledWith('/api/submit', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					comments: [{ file: 'file.ts', start_line: 10, end_line: 10, body: 'fix this' }]
				})
			});
			expect(result.comment_count).toBe(1);
			expect(commentStore.submitted).toBe(true);

			vi.unstubAllGlobals();
		});

		it('throws on non-ok response and does not set submitted', async () => {
			vi.stubGlobal(
				'fetch',
				vi.fn().mockResolvedValue({ ok: false, status: 500 })
			);

			commentStore.add('file.ts', 1, 1, 'test');

			await expect(commentStore.submit()).rejects.toThrow('Submit failed: 500');
			expect(commentStore.submitted).toBe(false);

			vi.unstubAllGlobals();
		});
	});
});
