import { describe, it, expect, beforeEach, vi } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { newComment } from './new-comment';

describe('commentStore', () => {
	beforeEach(() => {
		commentStore.clear();
	});

	it('starts with zero comments', () => {
		expect(commentStore.count).toBe(0);
		expect(commentStore.comments).toEqual([]);
	});

	it('adds a comment with generated id', () => {
		const id = commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 10, endLine: 10, body: 'fix this' }));

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
		commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 10, endLine: 15, body: 'refactor this block' }));

		expect(commentStore.comments[0].start_line).toBe(10);
		expect(commentStore.comments[0].end_line).toBe(15);
	});

	it('keeps comments on the two sides of the same line number apart', () => {
		commentStore.add(newComment({ file: 'file.ts', side: 'old', startLine: 42, endLine: 42, body: 'about the removed line' }));
		commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 42, endLine: 42, body: 'about the replacement' }));

		const removed = commentStore.getForLine('file.ts', 'old', 42);
		const added = commentStore.getForLine('file.ts', 'new', 42);

		expect(removed).toHaveLength(1);
		expect(removed[0].body).toBe('about the removed line');
		expect(added).toHaveLength(1);
		expect(added[0].body).toBe('about the replacement');
	});

	it('sends the side to the server so line numbers stay unambiguous', () => {
		commentStore.add(newComment({ file: 'file.ts', side: 'old', startLine: 7, endLine: 9, body: 'why was this dropped' }));

		expect(commentStore.comments[0].side).toBe('old');
		expect(commentStore.comments[0].start_line).toBe(7);
		expect(commentStore.comments[0].end_line).toBe(9);
	});

	it('updates a comment body', () => {
		const id = commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 1, endLine: 1, body: 'original' }));
		commentStore.update(id, 'updated', 'note', []);

		expect(commentStore.comments[0].body).toBe('updated');
	});

	it('removes a comment', () => {
		const id = commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 1, endLine: 1, body: 'to delete' }));
		commentStore.remove(id);

		expect(commentStore.count).toBe(0);
	});

	it('filters comments by file', () => {
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 1, endLine: 1, body: 'comment A' }));
		commentStore.add(newComment({ file: 'b.ts', side: 'new', startLine: 1, endLine: 1, body: 'comment B' }));
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 5, endLine: 5, body: 'comment A2' }));

		expect(commentStore.getForFile('a.ts')).toHaveLength(2);
		expect(commentStore.getForFile('b.ts')).toHaveLength(1);
		expect(commentStore.getForFile('c.ts')).toHaveLength(0);
	});

	it('getForLine returns comments anchored at their end line only', () => {
		commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 10, endLine: 15, body: 'range comment' }));
		commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 20, endLine: 20, body: 'single line' }));

		// Range comment only renders at end_line (15), not at start or middle
		expect(commentStore.getForLine('file.ts', 'new', 10)).toHaveLength(0);
		expect(commentStore.getForLine('file.ts', 'new', 12)).toHaveLength(0);
		expect(commentStore.getForLine('file.ts', 'new', 15)).toHaveLength(1);
		// Outside range
		expect(commentStore.getForLine('file.ts', 'new', 16)).toHaveLength(0);
		// Single line comment at line 20
		expect(commentStore.getForLine('file.ts', 'new', 20)).toHaveLength(1);
	});

	it('clear resets everything', () => {
		commentStore.add(newComment({ file: 'a.ts', side: 'new', startLine: 1, endLine: 1, body: 'x' }));
		commentStore.add(newComment({ file: 'b.ts', side: 'new', startLine: 2, endLine: 2, body: 'y' }));
		commentStore.setReviewBody('some summary');
		commentStore.clear();

		expect(commentStore.count).toBe(0);
		expect(commentStore.reviewBody).toBe('');
		expect(commentStore.submitted).toBe(false);
	});

	describe('reviewBody', () => {
		it('starts empty', () => {
			expect(commentStore.reviewBody).toBe('');
		});

		it('setReviewBody updates the body', () => {
			commentStore.setReviewBody('Wrong approach');

			expect(commentStore.reviewBody).toBe('Wrong approach');
		});

		it('hasContent is true with only review body', () => {
			expect(commentStore.hasContent).toBe(false);

			commentStore.setReviewBody('Some feedback');

			expect(commentStore.hasContent).toBe(true);
		});

		it('hasContent is true with only inline comments', () => {
			commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 1, endLine: 1, body: 'fix' }));

			expect(commentStore.hasContent).toBe(true);
		});

		it('whitespace-only body does not count as content', () => {
			commentStore.setReviewBody('   \n  ');

			expect(commentStore.hasContent).toBe(false);
		});
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

			commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 10, endLine: 10, body: 'fix this' }));
			const result = await commentStore.submit();

			expect(fetch).toHaveBeenCalledWith('/api/submit', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					comments: [
						{
							file: 'file.ts',
							side: 'new',
							severity: 'note',
							start_line: 10,
							end_line: 10,
							body: 'fix this',
							images: [],
							turns: [],
							raised_by: 'reader',
							resolved: false,
							outdated: false,
							quote: []
						}
					],
					end: true
				})
			});
			expect(result.comment_count).toBe(1);
			expect(commentStore.submitted).toBe(true);

			vi.unstubAllGlobals();
		});

		it('includes body in payload when review body is set', async () => {
			vi.stubGlobal(
				'fetch',
				vi.fn().mockResolvedValue({
					ok: true,
					json: () => Promise.resolve({ markdown: '## Comments', comment_count: 1 })
				})
			);

			commentStore.setReviewBody('General feedback');
			await commentStore.submit();

			const call = vi.mocked(fetch).mock.calls[0];
			const payload = JSON.parse(call[1]!.body as string);
			expect(payload.body).toBe('General feedback');

			vi.unstubAllGlobals();
		});

		it('omits body from payload when review body is empty', async () => {
			vi.stubGlobal(
				'fetch',
				vi.fn().mockResolvedValue({
					ok: true,
					json: () => Promise.resolve({ markdown: '## Comments', comment_count: 1 })
				})
			);

			commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 1, endLine: 1, body: 'fix' }));
			await commentStore.submit();

			const call = vi.mocked(fetch).mock.calls[0];
			const payload = JSON.parse(call[1]!.body as string);
			expect(payload.body).toBeUndefined();

			vi.unstubAllGlobals();
		});

		it('throws on non-ok response and does not set submitted', async () => {
			vi.stubGlobal(
				'fetch',
				vi.fn().mockResolvedValue({ ok: false, status: 500 })
			);

			commentStore.add(newComment({ file: 'file.ts', side: 'new', startLine: 1, endLine: 1, body: 'test' }));

			await expect(commentStore.submit()).rejects.toThrow('Submit failed: 500');
			expect(commentStore.submitted).toBe(false);

			vi.unstubAllGlobals();
		});
	});
});
