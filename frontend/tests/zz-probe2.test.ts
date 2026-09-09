import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import ReviewModal from '$lib/components/ReviewModal.svelte';

describe('comment id collision after restoring a draft', () => {
	beforeEach(() => {
		commentStore.clear();
		localStorage.clear();
	});

	it('reuses an id when a comment was deleted before the reload', () => {
		commentStore.restore('repo @ HEAD'); // start remembering
		const a = commentStore.add('a.ts', 'new', 1, 1, 'first');
		const b = commentStore.add('a.ts', 'new', 2, 2, 'second');
		commentStore.remove(a);
		expect(commentStore.comments.map((c) => c.id)).toEqual([b]);

		// reload
		commentStore.clear();
		const restored = commentStore.restore('repo @ HEAD');
		expect(restored).toBe(1);

		const c = commentStore.add('a.ts', 'new', 3, 3, 'third');
		console.log('ids after restore + add:', JSON.stringify(commentStore.comments.map((x) => x.id)), 'new id:', c);
		expect(new Set(commentStore.comments.map((x) => x.id)).size).toBe(commentStore.comments.length);
	});

	it('editing one collided comment edits both', () => {
		commentStore.restore('t');
		const a = commentStore.add('a.ts', 'new', 1, 1, 'first');
		commentStore.add('a.ts', 'new', 2, 2, 'second');
		commentStore.remove(a);
		commentStore.clear();
		commentStore.restore('t');
		const dup = commentStore.add('a.ts', 'new', 3, 3, 'third');
		commentStore.update(dup, 'EDITED');
		console.log('bodies:', JSON.stringify(commentStore.comments.map((x) => [x.id, x.body])));
	});

	it('ReviewModal with two comments sharing an id', async () => {
		commentStore.restore('t');
		const a = commentStore.add('a.ts', 'new', 1, 1, 'first');
		commentStore.add('a.ts', 'new', 2, 2, 'second');
		commentStore.remove(a);
		commentStore.clear();
		commentStore.restore('t');
		commentStore.add('a.ts', 'new', 3, 3, 'third');
		let err: unknown = null;
		try {
			render(ReviewModal, { props: { onSubmit: () => {}, onClose: () => {} } });
		} catch (e) {
			err = e;
		}
		console.log('modal render error:', err instanceof Error ? err.message : String(err));
		expect(err).not.toBeNull();
	});
});

describe('draft from an older schema', () => {
	beforeEach(() => {
		commentStore.clear();
		localStorage.clear();
	});
	it('restores comments with no severity or side and submits them', async () => {
		localStorage.setItem(
			'claude-review:draft',
			JSON.stringify({
				title: 't',
				reviewBody: '',
				comments: [{ id: 'comment-1', file: 'a.ts', start_line: 1, end_line: 1, body: 'old draft' }]
			})
		);
		expect(commentStore.restore('t')).toBe(1);
		let sent: string | undefined;
		globalThis.fetch = (async (_url: string, init: RequestInit) => {
			sent = init.body as string;
			return { ok: true, json: async () => ({ markdown: '', comment_count: 1 }) } as Response;
		}) as typeof fetch;
		await commentStore.submit();
		console.log('submitted payload:', sent);
	});
});
