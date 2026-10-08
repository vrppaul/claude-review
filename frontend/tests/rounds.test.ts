import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import { lineAnchor } from '$lib/anchors/line';
import type { Anchor, Comment } from '$lib/types';
import { newComment } from './new-comment';

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
		commentStore.add(newComment({ file: 'a.py', side: 'new', startLine: 1, endLine: 1, body: 'tighten this' }));

		await commentStore.submit(false);

		expect(commentStore.count).toBe(1);
		expect(commentStore.submitted).toBe(false);
	});

	it('carries what is new since the last round, not the review again', async () => {
		const fetchMock = okFetch();
		commentStore.add(newComment({ file: 'a.py', side: 'new', startLine: 1, endLine: 1, body: 'tighten this' }));
		await commentStore.submit(false);

		commentStore.add(newComment({ file: 'b.py', side: 'new', startLine: 2, endLine: 2, body: 'and this' }));
		await commentStore.submit(false);

		expect(sentPayload(fetchMock, 1).comments.map((c: Comment) => c.anchor.file)).toEqual(['b.py']);
	});

	it('sends a thread again once something has been said in it', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add(newComment({ file: 'a.py', side: 'new', startLine: 1, endLine: 1, body: 'tighten this' }));
		await commentStore.submit(false);

		commentStore.receiveReply(id, 'Tightened');
		commentStore.addTurn(id, { author: 'reader', body: 'Still reads oddly', images: [] });
		await commentStore.submit(false);

		const again = sentPayload(fetchMock, 1).comments[0];
		expect(again.anchor.file).toBe('a.py');
		expect(again.turns).toHaveLength(2);
	});

	it('does not resend a thread just because it was answered', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add(newComment({ file: 'a.py', side: 'new', startLine: 1, endLine: 1, body: 'tighten this' }));
		await commentStore.submit(false);

		commentStore.receiveReply(id, 'Tightened');
		commentStore.add(newComment({ file: 'b.py', side: 'new', startLine: 2, endLine: 2, body: 'and this' }));
		await commentStore.submit(false);

		expect(sentPayload(fetchMock, 1).comments.map((c: Comment) => c.anchor.file)).toEqual(['b.py']);
	});

	it('counts up so the next round says which one it is', async () => {
		okFetch(2);
		commentStore.add(newComment({ file: 'a.py', side: 'new', startLine: 1, endLine: 1, body: 'tighten this' }));

		await commentStore.submit(false);

		expect(reviewStore.round).toBe(3);
	});
});

describe('a thread meeting a diff that has been taken again', () => {
	beforeEach(() => {
		commentStore.clear();
		localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	/** The server answering with where each thread now hangs, in the order asked. */
	function followedTo(anchors: Anchor[]) {
		const mock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ anchors }) });
		vi.stubGlobal('fetch', mock);
		return mock;
	}

	it('asks the server where every thread now hangs', async () => {
		const fetchMock = followedTo([lineAnchor('a.py', 'new', 2, 2, ['def run():'])]);
		commentStore.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		await commentStore.follow();

		expect(fetchMock.mock.calls[0][0]).toBe('/api/anchors/follow');
		expect(sentPayload(fetchMock).anchors[0].quote).toEqual(['def run():']);
	});

	it('moves a thread to where its lines went, and counts it', async () => {
		followedTo([lineAnchor('a.py', 'new', 3, 3, ['def run():'])]);
		commentStore.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		const moved = await commentStore.follow();

		expect(commentStore.comments[0].anchor.start_line).toBe(3);
		expect(moved).toEqual({ followed: 1, outdated: 0 });
	});

	it('counts a thread whose lines are gone as outdated, not as followed', async () => {
		followedTo([{ ...lineAnchor('a.py', 'new', 2, 2, ['def walk():']), outdated: true }]);
		commentStore.add(newComment({ file: 'a.py', startLine: 2, quote: ['def walk():'] }));

		const moved = await commentStore.follow();

		expect(commentStore.comments[0].anchor.outdated).toBe(true);
		expect(moved).toEqual({ followed: 0, outdated: 1 });
	});

	it('leaves a thread written while the answer was on its way where it is', async () => {
		let answer: (value: unknown) => void = () => undefined;
		vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise((resolve) => (answer = resolve))));
		commentStore.add(newComment({ file: 'a.py', startLine: 2, quote: ['def run():'] }));

		const following = commentStore.follow();
		commentStore.add(newComment({ file: 'a.py', startLine: 9, quote: ['late'] }));
		answer({ ok: true, json: () => Promise.resolve({ anchors: [lineAnchor('a.py', 'new', 3, 3, ['def run():'])] }) });
		await following;

		expect(commentStore.comments.map((c) => c.anchor.start_line)).toEqual([3, 9]);
	});
});
