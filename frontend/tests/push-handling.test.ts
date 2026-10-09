import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { handlePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { ServerPush, SessionHello } from '$lib/types';
import { contextLine, diffFile, diffResponse, hunk } from './diff';
import { fakeServer } from './fake-server';
import { newComment } from './new-comment';
import { inReview, openReview } from './review';

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** Let a push whose work goes on after it is taken — a retake — finish it. */
function settled(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve));
}

let review: Review;

beforeEach(() => {
	review = openReview({ files: [untouched('a.py'), untouched('b.py')] });
});

describe('what the server pushes, taken in', () => {
	it('puts an answer under the thread it answers, unread', () => {
		const id = review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));

		handlePush(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' });

		expect(review.threads.all[0].turns.at(-1)?.body).toBe('Because.');
		expect(review.threads.unread.map((thread) => thread.id)).toEqual([id]);
	});

	it('offers the panel when an agent turns up, and stops offering rounds when it goes', () => {
		handlePush(review, { type: 'answerer', attached: true });
		expect(review.answerer.attached).toBe(true);
		expect(review.layout.agentPanel.open).toBe(true);

		handlePush(review, { type: 'answerer', attached: false });
		expect(review.answerer.attached).toBe(false);
	});

	it('counts an answer in the panel while the panel is shut', () => {
		review.layout.agentPanel.setOpen(false);

		handlePush(review, { type: 'chat', message_id: null, body: 'Done.', files: [] });

		expect(review.conversation.turns.at(-1)?.body).toBe('Done.');
		expect(review.layout.agentPanel.unread).toBe(1);
	});

	it('says the tree moved, the moment it does, without touching the diff', () => {
		const { getByTestId } = render(DiffNotice, inReview(review));

		handlePush(review, { type: 'changed', moved_count: 3 });
		flushSync();

		expect(getByTestId('tree-moved').textContent).toContain('3');
		expect(review.diff.files.map((file) => file.path)).toEqual(['a.py', 'b.py']);
	});

	it('moves on to the round the server began, never back', () => {
		handlePush(review, { type: 'round', number: 3 });
		handlePush(review, { type: 'round', number: 2 });

		expect(review.rounds.current).toBe(3);
	});

	it('puts a thread the agent raised on the diff, and says so in the panel', () => {
		const anchor = newComment({ file: 'a.py' }).anchor;

		handlePush(review, { type: 'point', thread_id: 'raised-1', anchor, body: 'Look', severity: 'note' });

		expect(review.threads.all[0].raised_by).toBe('author');
		expect(review.conversation.turns.at(-1)?.threads).toEqual(['raised-1']);
	});

	it("counts the review's files after a retake, not those of a narrower base on screen", async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		// A narrower base shows one file of the review's three
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], base_key: 'round:1' }));
		const retake: ServerPush = { type: 'diff', file_count: 3, changes: null };

		handlePush(review, retake);
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('diff retaken · 3 files');
	});
});

describe('what the page tells the server it holds', () => {
	it('is the round it has reached and every thread, said again whenever either changes', () => {
		const said: SessionHello[] = [];
		const stop = review.tellServerThrough({ greet: (hello) => said.push(hello) });
		flushSync();

		review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		review.rounds.reach(2);
		flushSync();

		expect(said.at(0)).toEqual({ round: 1, threads: [] });
		expect(said.at(-1)?.round).toBe(2);
		expect(said.at(-1)?.threads?.map((thread) => thread.body)).toEqual(['Why?']);
		stop();
	});

	it('is not said again when a file is folded, which the server has no use for', () => {
		review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		const said: SessionHello[] = [];
		const stop = review.tellServerThrough({ greet: (hello) => said.push(hello) });
		flushSync();

		review.reading.toggleFolded('a.py');
		flushSync();

		expect(said).toHaveLength(1);
		stop();
	});
});
