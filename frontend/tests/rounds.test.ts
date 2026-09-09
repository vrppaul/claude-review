import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import { reanchor } from '$lib/utils/reanchor';
import type { Comment, DiffHunk } from '$lib/types';

function sentPayload(mock: ReturnType<typeof vi.fn>, call = 0) {
	return JSON.parse(mock.mock.calls[call][1].body);
}

function okFetch(round = 1) {
	const mock = vi.fn().mockResolvedValue({
		ok: true,
		json: () => Promise.resolve({ markdown: '## x', comment_count: 1, round, ended: false })
	});
	vi.stubGlobal('fetch', mock);
	return mock;
}

describe('sending a round rather than ending the review', () => {
	beforeEach(() => {
		commentStore.clear();
		reviewStore.clear();
		localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('keeps the threads on screen', async () => {
		okFetch();
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');

		await commentStore.submit(false);

		expect(commentStore.count).toBe(1);
		expect(commentStore.submitted).toBe(false);
	});

	it('carries what is new since the last round, not the review again', async () => {
		const fetchMock = okFetch();
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');
		await commentStore.submit(false);

		commentStore.add('b.py', 'new', 2, 2, 'and this');
		await commentStore.submit(false);

		expect(sentPayload(fetchMock, 1).comments.map((c: Comment) => c.file)).toEqual(['b.py']);
	});

	it('sends a thread again once something has been said in it', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add('a.py', 'new', 1, 1, 'tighten this');
		await commentStore.submit(false);

		commentStore.receiveReply(id, 'Tightened');
		commentStore.addTurn(id, 'reader', 'Still reads oddly');
		await commentStore.submit(false);

		const again = sentPayload(fetchMock, 1).comments[0];
		expect(again.file).toBe('a.py');
		expect(again.turns).toHaveLength(2);
	});

	it('does not resend a thread just because it was answered', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add('a.py', 'new', 1, 1, 'tighten this');
		await commentStore.submit(false);

		commentStore.receiveReply(id, 'Tightened');
		commentStore.add('b.py', 'new', 2, 2, 'and this');
		await commentStore.submit(false);

		expect(sentPayload(fetchMock, 1).comments.map((c: Comment) => c.file)).toEqual(['b.py']);
	});

	it('counts up so the next round says which one it is', async () => {
		okFetch(2);
		commentStore.add('a.py', 'new', 1, 1, 'tighten this');

		await commentStore.submit(false);

		expect(reviewStore.round).toBe(3);
	});
});

describe('a thread meeting a diff that has been taken again', () => {
	const hunks: DiffHunk[] = [
		{
			header: '@@ -1,3 +1,4 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'import os' },
				{ type: 'add', old_no: null, new_no: 2, content: 'import sys' },
				{ type: 'context', old_no: 2, new_no: 3, content: 'def run():' },
				{ type: 'context', old_no: 3, new_no: 4, content: '    return 1' }
			]
		}
	];

	function comment(quote: string[], start: number, end: number): Comment {
		return {
			id: 'comment-1',
			file: 'a.py',
			side: 'new',
			severity: 'note',
			start_line: start,
			end_line: end,
			body: 'why',
			turns: [],
			resolved: false,
			outdated: false,
			quote,
			awaiting: [],
			collapsed: false,
			unread: false,
			round: 1,
			at: 0
		};
	}

	it('follows the lines it was written about when they move', () => {
		const moved = reanchor(comment(['def run():'], 2, 2), hunks);

		expect(moved).toEqual({ start_line: 3, end_line: 3, outdated: false });
	});

	it('keeps a range together', () => {
		const moved = reanchor(comment(['def run():', '    return 1'], 2, 3), hunks);

		expect(moved).toEqual({ start_line: 3, end_line: 4, outdated: false });
	});

	it('says so when the lines are gone rather than pointing at their replacement', () => {
		const gone = reanchor(comment(['def walk():'], 2, 2), hunks);

		expect(gone.outdated).toBe(true);
		expect(gone.start_line).toBe(2);
	});

	it('marks a thread whose whole file has left the diff', () => {
		const gone = reanchor(comment(['def run():'], 2, 2), null);

		expect(gone.outdated).toBe(true);
	});

	it('leaves a thread that never kept its lines where it is', () => {
		const kept = reanchor(comment([], 2, 2), hunks);

		expect(kept).toEqual({ start_line: 2, end_line: 2, outdated: false });
	});
});
