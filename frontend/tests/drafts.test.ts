import { describe, it, expect, beforeEach, vi } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { loadDraft, saveDraft, clearDraft } from '$lib/utils/drafts';

describe('an unsent review', () => {
	beforeEach(() => {
		localStorage.clear();
		commentStore.clear();
	});

	it('survives a reload of the same review', () => {
		commentStore.restore('repo: uncommitted changes');
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');
		commentStore.setReviewBody('Overall fine');

		commentStore.clear();
		const count = commentStore.restore('repo: uncommitted changes');

		expect(count).toBe(1);
		expect(commentStore.comments[0].body).toBe('tighten this');
		expect(commentStore.reviewBody).toBe('Overall fine');
	});

	it('is not handed to a different review', () => {
		commentStore.restore('repo: uncommitted changes');
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');

		commentStore.clear();
		const count = commentStore.restore('other-repo: changes since v1');

		expect(count).toBe(0);
		expect(commentStore.comments).toEqual([]);
	});

	it('does not come back after it has been sent', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ markdown: '## x', comment_count: 1 })
			})
		);
		commentStore.restore('repo: uncommitted changes');
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');

		await commentStore.submit();
		commentStore.clear();

		expect(commentStore.restore('repo: uncommitted changes')).toBe(0);
		vi.unstubAllGlobals();
	});

	it('keeps ids apart from the ones restored with it', () => {
		commentStore.restore('repo: uncommitted changes');
		commentStore.add('a.py', 'new', 1, 1, 'first');
		commentStore.add('a.py', 'new', 2, 2, 'second');

		commentStore.clear();
		commentStore.restore('repo: uncommitted changes');
		commentStore.add('a.py', 'new', 3, 3, 'third');

		const ids = commentStore.comments.map((c) => c.id);
		expect(new Set(ids).size).toBe(3);
	});

	it('leaves the review working when site data is blocked', () => {
		const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});

		commentStore.restore('repo: uncommitted changes');
		expect(() => commentStore.add('a.py', 'new', 1, 1, 'still fine')).not.toThrow();
		expect(commentStore.count).toBe(1);

		setItem.mockRestore();
	});

	it('ignores a draft that is not what it should be', () => {
		localStorage.setItem('claude-review:draft', 'not json at all');

		expect(loadDraft('repo: uncommitted changes')).toBeNull();
	});

	it('forgets a draft when asked', () => {
		saveDraft({ title: 'repo', comments: [], sent: [], reviewBody: 'x' });
		clearDraft();

		expect(loadDraft('repo')).toBeNull();
	});
});

describe('a draft written by an older version', () => {
	beforeEach(() => {
		localStorage.clear();
	});

	it('is brought up to the current shape rather than thrown away', () => {
		localStorage.setItem(
			'claude-review:draft',
			JSON.stringify({
				title: 'repo: uncommitted changes',
				comments: [
					{
						id: 'comment-1',
						file: 'a.py',
						side: 'new',
						severity: 'note',
						start_line: 1,
						end_line: 1,
						body: 'written before threads existed'
					}
				],
				reviewBody: ''
			})
		);

		const draft = loadDraft('repo: uncommitted changes');

		expect(draft?.comments[0].body).toBe('written before threads existed');
		expect(draft?.comments[0].turns).toEqual([]);
		expect(draft?.comments[0].awaiting).toEqual([]);
		expect(draft?.sent).toEqual([]);
	});
});
