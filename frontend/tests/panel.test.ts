import { describe, it, expect, beforeEach } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { panelStore } from '$lib/stores/panel.svelte';
import { loadDraft } from '$lib/utils/drafts';
import { threadsIn } from '$lib/utils/thread-token';
import { anchorToken } from '$lib/anchors/views';
import { formatWeight } from '$lib/utils/weight';
import type { Comment } from '$lib/types';
import { contextLine, addedLine, diffFile, hunk } from './diff';
import { fakeServer, listeningToThePanel, SERVER_ERROR } from './fake-server';
import { newComment } from './new-comment';

const TITLE = 'claude-review: uncommitted changes';

const file = diffFile({
	path: 'src/routes.py',
	hunks: [hunk([contextLine(1, 1, 'x = 1'), addedLine(2, 'y = 3')])]
});

// The panel keeps its width between these, whatever the reader drags it to
const NARROWEST_PANEL = 280;
const WIDEST_PANEL = 720;

/** Write a message in the panel and send it, the way the composer does. */
function say(text: string, threads: Comment[] = []): Promise<void> {
	panelStore.setComposerText(text);
	return panelStore.send(threads);
}

describe('the panel talks to the agent about the review', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff', TITLE);
		commentStore.restore(TITLE);
		panelStore.restore(TITLE);
	});

	it('sends what was typed at once, without waiting for a round', async () => {
		const server = listeningToThePanel();

		await say('Run the tests and say what fails.');

		expect(server.requests).toMatchObject([
			{ method: 'POST', path: '/api/message', body: { text: 'Run the tests and say what fails.' } }
		]);
		expect(panelStore.turns.map((turn) => turn.body)).toEqual(['Run the tests and say what fails.']);
	});

	it('carries the whole thread a message points at, not only its id', async () => {
		const server = listeningToThePanel();
		const id = commentStore.add(
			newComment({
				file: 'src/routes.py',
				startLine: 2,
				body: 'Why catch here?',
				severity: 'question',
				quote: ['y = 3']
			})
		);
		commentStore.addTurn(id, { author: 'author', body: 'Because the caller cannot.', images: [] });
		const thread = commentStore.comments[0];

		await say(`Look at ${anchorToken(thread.anchor)} again`, [thread]);

		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([
			{
				threads: [
					{
						thread_id: id,
						anchor: { quote: ['y = 3'] },
						body: 'Why catch here?',
						history: [{ body: 'Because the caller cannot.' }]
					}
				]
			}
		]);
	});

	it('reads the references back from the words, so deleting one drops it', () => {
		commentStore.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why catch here?' }));
		const thread = commentStore.comments[0];

		expect(
			threadsIn(`Look at ${anchorToken(thread.anchor)} again`, commentStore.comments)
		).toHaveLength(1);
		expect(threadsIn('Look at it again', commentStore.comments)).toHaveLength(0);
	});

	it('does not mistake one range for a longer one that starts the same', () => {
		commentStore.add(
			newComment({ file: 'src/routes.py', startLine: 1, endLine: 2, body: 'the short one' })
		);
		const short = commentStore.comments[0];

		expect(threadsIn('@src/routes.py:1-20 is the other one', [short])).toHaveLength(0);
	});

	it('puts an answer under the message it names', async () => {
		listeningToThePanel();
		await say('What did the round change?');

		panelStore.receive(panelStore.turns[0].id, 'Two files; both green.');

		expect(panelStore.turns.map((turn) => turn.author)).toEqual(['reader', 'author']);
		expect(panelStore.working).toBeUndefined();
	});

	it('waits visibly until the answer lands', async () => {
		listeningToThePanel();
		await say('Run the tests');

		expect(panelStore.working?.body).toBe('Run the tests');
	});

	it('stops waiting once the reader takes a message back', async () => {
		const server = listeningToThePanel();
		await say('Never mind this one');
		const message = panelStore.turns[0].id;

		await panelStore.cancel(message);

		expect(server.bodiesSentTo('POST /api/cancel')).toEqual([{ message_id: message }]);
		expect(panelStore.working).toBeUndefined();
		expect(panelStore.turns[0].cancelled).toBe(true);
	});

	it('keeps the conversation across a reload', async () => {
		listeningToThePanel();
		await say('Where did the None check go?');
		panelStore.receive(panelStore.turns[0].id, 'Into the caller.');

		panelStore.clear();
		panelStore.restore(TITLE);

		expect(panelStore.turns.map((turn) => turn.body)).toEqual([
			'Where did the None check go?',
			'Into the caller.'
		]);
	});

	it('does not hand the same message id out twice after a reload', async () => {
		listeningToThePanel();
		await say('first');
		panelStore.clear();
		panelStore.restore(TITLE);

		await say('second');

		const ids = panelStore.turns.map((turn) => turn.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('never writes the panel over the threads in the draft', async () => {
		listeningToThePanel();
		commentStore.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'an hour of reading' }));

		await say('and a message');

		expect(loadDraft(TITLE)?.comments).toHaveLength(1);
		expect(loadDraft(TITLE)?.panel).toHaveLength(1);
	});

	it('takes a failed send back off the conversation', async () => {
		fakeServer().refuse('POST /api/message', SERVER_ERROR);

		await expect(say('into the void')).rejects.toThrow();
		expect(panelStore.turns).toHaveLength(0);
	});

	it('still waits on a message the server did not hear taken back', async () => {
		const server = listeningToThePanel();
		await say('Keep this one');
		server.refuse('POST /api/cancel', SERVER_ERROR);

		await expect(panelStore.cancel(panelStore.turns[0].id)).rejects.toThrow();

		expect(panelStore.turns[0].cancelled).toBeFalsy();
		expect(panelStore.working?.body).toBe('Keep this one');
	});

	it('takes a send that never reached the server back off the conversation', async () => {
		fakeServer().drop('POST /api/message');

		await expect(say('into the void')).rejects.toThrow();
		expect(panelStore.turns).toHaveLength(0);
	});

	it('goes on showing the work under way when a new message fails to go', async () => {
		panelStore.reportProgress(undefined, 'Running the tests', ['tests/test_a.py']);
		fakeServer().refuse('POST /api/message', SERVER_ERROR);

		await expect(say('and this?')).rejects.toThrow();

		expect(panelStore.progress?.text).toBe('Running the tests');
	});

	it('weighs the review from what is on screen, and says so roughly', () => {
		commentStore.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'x'.repeat(400) }));

		// The path's 13 characters, two lines of 5 with their line breaks, and
		// the comment's 400: 425 characters, at about four to a token
		expect(panelStore.weight).toBe(106);
		expect(formatWeight(18_240)).toBe('~18.2k');
		expect(formatWeight(640)).toBe('~640');
	});

	it('remembers how wide the reader made it, within what the layout can take', () => {
		panelStore.setWidth(WIDEST_PANEL + 1);
		expect(panelStore.width).toBe(WIDEST_PANEL);

		panelStore.setWidth(NARROWEST_PANEL - 1);
		expect(panelStore.width).toBe(NARROWEST_PANEL);
	});
});
