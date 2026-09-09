import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { panelStore } from '$lib/stores/panel.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import { loadDraft } from '$lib/utils/drafts';
import { threadsIn, threadToken } from '$lib/utils/thread-token';
import { formatWeight, reviewWeight } from '$lib/utils/weight';
import type { DiffFile } from '$lib/types';

const TITLE = 'claude-review: uncommitted changes';

const file: DiffFile = {
	path: 'src/routes.py',
	status: 'modified',
	hunks: [
		{
			header: '@@ -1,2 +1,2 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'x = 1' },
				{ type: 'add', old_no: null, new_no: 2, content: 'y = 3' }
			]
		}
	],
	is_binary: false,
	old_mode: null,
	new_mode: null
};

function okFetch() {
	const mock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
	vi.stubGlobal('fetch', mock);
	return mock;
}

function sent(mock: ReturnType<typeof vi.fn>, call = 0) {
	return JSON.parse(mock.mock.calls[call][1].body);
}

describe('the panel talks to the agent about the review', () => {
	beforeEach(() => {
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
		reviewStore.clear();
		panelStore.clear();
		diffStore.setFiles([file], 'diff', TITLE);
		commentStore.restore(TITLE);
		panelStore.restore(TITLE);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('sends what was typed at once, without waiting for a round', async () => {
		const fetchMock = okFetch();

		await panelStore.send('Run the tests and say what fails.', []);

		expect(fetchMock.mock.calls[0][0]).toBe('/api/message');
		expect(sent(fetchMock).text).toBe('Run the tests and say what fails.');
		expect(panelStore.turns.map((t) => t.body)).toEqual(['Run the tests and say what fails.']);
	});

	it('carries the whole thread a message points at, not only its id', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add('src/routes.py', 'new', 2, 2, 'Why catch here?', 'question', [
			'y = 3'
		]);
		commentStore.addTurn(id, 'author', 'Because the caller cannot.');
		const thread = commentStore.comments[0];

		await panelStore.send(`Look at ${threadToken(thread)} again`, [thread]);

		const [carried] = sent(fetchMock).threads;
		expect(carried.thread_id).toBe(id);
		expect(carried.quote).toEqual(['y = 3']);
		expect(carried.body).toBe('Why catch here?');
		expect(carried.history[0].body).toBe('Because the caller cannot.');
	});

	it('reads the references back from the words, so deleting one drops it', () => {
		commentStore.add('src/routes.py', 'new', 2, 2, 'Why catch here?');
		const thread = commentStore.comments[0];

		expect(threadsIn(`Look at ${threadToken(thread)} again`, commentStore.comments)).toHaveLength(
			1
		);
		expect(threadsIn('Look at it again', commentStore.comments)).toHaveLength(0);
	});

	it('does not mistake one range for a longer one that starts the same', () => {
		commentStore.add('src/routes.py', 'new', 1, 2, 'the short one');
		const short = commentStore.comments[0];

		expect(threadsIn('@src/routes.py:1-20 is the other one', [short])).toHaveLength(0);
	});

	it('puts an answer under the message it names', async () => {
		okFetch();
		await panelStore.send('What did the round change?', []);

		panelStore.receive(panelStore.turns[0].id, 'Two files; both green.');

		expect(panelStore.turns.map((t) => t.author)).toEqual(['reader', 'author']);
		expect(panelStore.working).toBeUndefined();
	});

	it('waits visibly until the answer lands', async () => {
		okFetch();
		await panelStore.send('Run the tests', []);

		expect(panelStore.working?.body).toBe('Run the tests');
	});

	it('stops waiting once the reader takes a message back', async () => {
		const fetchMock = okFetch();
		await panelStore.send('Never mind this one', []);

		await panelStore.cancel(panelStore.turns[0].id);

		expect(fetchMock.mock.calls[1][0]).toBe('/api/cancel');
		expect(panelStore.working).toBeUndefined();
		expect(panelStore.turns[0].cancelled).toBe(true);
	});

	it('keeps the conversation across a reload', async () => {
		okFetch();
		await panelStore.send('Where did the None check go?', []);
		panelStore.receive(panelStore.turns[0].id, 'Into the caller.');

		panelStore.clear();
		panelStore.restore(TITLE);

		expect(panelStore.turns.map((t) => t.body)).toEqual([
			'Where did the None check go?',
			'Into the caller.'
		]);
	});

	it('does not hand the same message id out twice after a reload', async () => {
		okFetch();
		await panelStore.send('first', []);
		panelStore.clear();
		panelStore.restore(TITLE);

		await panelStore.send('second', []);

		const ids = panelStore.turns.map((t) => t.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('never writes the panel over the threads in the draft', async () => {
		okFetch();
		commentStore.add('src/routes.py', 'new', 2, 2, 'an hour of reading');

		await panelStore.send('and a message', []);

		expect(loadDraft(TITLE)?.comments).toHaveLength(1);
		expect(loadDraft(TITLE)?.panel).toHaveLength(1);
	});

	it('takes a failed send back off the conversation', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));

		await expect(panelStore.send('into the void', [])).rejects.toThrow();
		expect(panelStore.turns).toHaveLength(0);
	});

	it('weighs the review from what is on screen, and says so roughly', () => {
		commentStore.add('src/routes.py', 'new', 2, 2, 'x'.repeat(400));

		expect(panelStore.weight).toBe(
			reviewWeight(diffStore.files, commentStore.comments)
		);
		expect(formatWeight(18_240)).toBe('~18.2k');
		expect(formatWeight(640)).toBe('~640');
	});

	it('remembers how wide the reader made it, within what the layout can take', () => {
		panelStore.setWidth(5000);
		expect(panelStore.width).toBe(720);

		panelStore.setWidth(100);
		expect(panelStore.width).toBe(280);
	});
});
