import { describe, it, expect, beforeEach } from 'vitest';
import { readDraft } from '$lib/drafts/draft-storage';
import { threadsIn } from '$lib/anchors/thread-token';
import { anchorToken } from '$lib/anchors/views';
import { formatWeight } from '$lib/review/weight';
import type { Thread } from '$lib/types';
import { contextLine, addedLine, diffFile, hunk } from './diff';
import { fakeServer, listeningToThePanel, SERVER_ERROR } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { KEPT_AS, keepingImages, screenshot, SEND_LIMITS } from './pasted-images';
import { leavePage, openReview } from './review';
import { settled } from './settled';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const TITLE = 'claude-review: uncommitted changes';

const file = diffFile({
	path: 'src/routes.py',
	hunks: [hunk([contextLine(1, 1, 'x = 1'), addedLine(2, 'y = 3')])]
});

// The panel keeps its width between these, whatever the reader drags it to
const NARROWEST_PANEL = 280;
const WIDEST_PANEL = 720;

/** Write a message in the panel and send it, the way the composer does. */
function say(text: string, threads: Thread[] = []): Promise<void> {
	review.conversation.composer.setText(text);
	return review.conversation.send(threads);
}

describe('the panel talks to the agent about the review', () => {
	beforeEach(() => {
		review = openReview({ files: [file], facts: { title: TITLE } });
	});

	it('sends what was typed at once, without waiting for a round', async () => {
		const server = listeningToThePanel();

		await say('Run the tests and say what fails.');

		expect(server.requests).toMatchObject([
			{ method: 'POST', path: '/api/message', body: { body: 'Run the tests and say what fails.' } }
		]);
		expect(review.conversation.turns.map((turn) => turn.body)).toEqual(['Run the tests and say what fails.']);
	});

	it('carries the whole thread a message points at, not only its id', async () => {
		const server = listeningToThePanel();
		const id = review.threads.add(
			newComment({
				file: 'src/routes.py',
				startLine: 2,
				body: 'Why catch here?',
				severity: 'question',
				quote: ['y = 3']
			})
		);
		review.threads.addTurn(id, { author: 'author', body: 'Because the caller cannot.', images: [] });
		const thread = review.threads.all[0];

		await say(`Look at ${anchorToken(thread.anchor)} again`, [thread]);

		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([
			{
				threads: [
					{
						thread_id: id,
						anchor: { quote: ['y = 3'] },
						body: 'Why catch here?',
						turns: [{ body: 'Because the caller cannot.' }]
					}
				]
			}
		]);
	});

	it('reads the references back from the words, so deleting one drops it', () => {
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why catch here?' }));
		const thread = review.threads.all[0];

		expect(threadsIn(`Look at ${anchorToken(thread.anchor)} again`, review.threads.all)).toHaveLength(1);
		expect(threadsIn('Look at it again', review.threads.all)).toHaveLength(0);
	});

	it('does not mistake one range for a longer one that starts the same', () => {
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 1, endLine: 2, body: 'the short one' }));
		const short = review.threads.all[0];

		expect(threadsIn('@src/routes.py:1-20 is the other one', [short])).toHaveLength(0);
	});

	it('puts an answer under the message it names', async () => {
		listeningToThePanel();
		await say('What did the round change?');

		review.conversation.receive(review.conversation.turns[0].id, 'Two files; both green.', []);

		expect(review.conversation.turns.map((turn) => turn.author)).toEqual(['reader', 'author']);
		expect(review.conversation.working).toBeUndefined();
	});

	it('waits visibly until the answer lands', async () => {
		listeningToThePanel();
		await say('Run the tests');

		expect(review.conversation.working?.body).toBe('Run the tests');
	});

	it('stops waiting once the reader takes a message back', async () => {
		const server = listeningToThePanel();
		await say('Never mind this one');
		const message = review.conversation.turns[0].id;

		await review.conversation.cancel(message);

		expect(server.bodiesSentTo('POST /api/cancel')).toEqual([{ message_id: message }]);
		expect(review.conversation.working).toBeUndefined();
		expect(review.conversation.turns[0].cancelled).toBe(true);
	});

	it('keeps the conversation across a reload', async () => {
		listeningToThePanel();
		await say('Where did the None check go?');
		review.conversation.receive(review.conversation.turns[0].id, 'Into the caller.', []);

		review = openReview({ files: [file], facts: { title: TITLE } });

		expect(review.conversation.turns.map((turn) => turn.body)).toEqual([
			'Where did the None check go?',
			'Into the caller.'
		]);
	});

	it('does not hand the same message id out twice after a reload', async () => {
		listeningToThePanel();
		await say('first');
		review = openReview({ files: [file], facts: { title: TITLE } });

		await say('second');

		const ids = review.conversation.turns.map((turn) => turn.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('never writes the panel over the threads in the draft', async () => {
		listeningToThePanel();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'an hour of reading' }));

		await say('and a message');
		leavePage();

		const kept = readDraft(TITLE);
		expect(kept?.threads).toHaveLength(1);
		expect(kept?.panel).toHaveLength(1);
	});

	it('takes a failed send back off the conversation', async () => {
		fakeServer().refuse('POST /api/message', SERVER_ERROR);

		await expect(say('into the void')).rejects.toThrow();
		expect(review.conversation.turns).toHaveLength(0);
	});

	it('still waits on a message the server did not hear taken back', async () => {
		const server = listeningToThePanel();
		await say('Keep this one');
		server.refuse('POST /api/cancel', SERVER_ERROR);

		await expect(review.conversation.cancel(review.conversation.turns[0].id)).rejects.toThrow();

		expect(review.conversation.turns[0].cancelled).toBeFalsy();
		expect(review.conversation.working?.body).toBe('Keep this one');
	});

	it('takes a send that never reached the server back off the conversation', async () => {
		fakeServer().drop('POST /api/message');

		await expect(say('into the void')).rejects.toThrow();
		expect(review.conversation.turns).toHaveLength(0);
	});

	it('weighs the review from what is on screen, and says so roughly', () => {
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'x'.repeat(400) }));

		// The path's 13 characters, two lines of 5 with their line breaks, and
		// the comment's 400: 425 characters, at about four to a token
		expect(review.weight).toBe(106);
		expect(formatWeight(18_240)).toBe('~18.2k');
		expect(formatWeight(640)).toBe('~640');
	});

	it('remembers how wide the reader made it, within what the layout can take', () => {
		review.layout.agentPanel.setWidth(WIDEST_PANEL + 1);
		expect(review.layout.agentPanel.width).toBe(WIDEST_PANEL);

		review.layout.agentPanel.setWidth(NARROWEST_PANEL - 1);
		expect(review.layout.agentPanel.width).toBe(NARROWEST_PANEL);
	});
});

describe('an image pasted into the panel before a reload', () => {
	it('goes from the server when it is taken off after the reload', async () => {
		const server = keepingImages();
		await review.conversation.composer.attachments.attach([screenshot()], SEND_LIMITS);

		leavePage();
		review = openReview();
		review.conversation.composer.attachments.detach(KEPT_AS);
		await settled();

		expect(server.requests.at(-1)).toMatchObject({ method: 'DELETE', path: `/api/images/${KEPT_AS}` });
	});
});
