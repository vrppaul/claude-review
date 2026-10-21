import { describe, it, expect, beforeEach } from 'vitest';
import { flushSync, tick } from 'svelte';
import { AGENT_STOPPED_LISTENING } from '$lib/components/agent-waits';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentThread from '$lib/components/CommentThread.svelte';
import DiffView from '$lib/components/DiffView.svelte';
import { addedLine, contextLine, diffFile, hunk } from './diff';
import { said } from './elements';
import { fakeServer, SERVER_ERROR, type FakeServer } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import type { Turn } from '$lib/types';
import { inReview, openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const file = diffFile({
	path: 'src/handler.ts',
	hunks: [hunk([contextLine(1, 1, 'const x = 1;'), addedLine(2, 'const y = 3;')])]
});

/** A server taking every question about a thread. */
function answering(): FakeServer {
	const server = fakeServer();
	server.answer('POST /api/ask', null);
	return server;
}

/** A comment on the added line of the file. */
function onTheAddedLine(body: string, images: string[] = []) {
	return newComment({ file: 'src/handler.ts', startLine: 2, body, images, quote: ['const y = 3;'] });
}

/** Whether each of these answers in a thread arrived after the reader last looked at it. */
function arrivedSinceLooked(threadId: string, answers: Turn[]): boolean[] {
	return answers.map((answer) => review.threads.reading.isNewAnswer(threadId, answer.id));
}

describe('a thread is a conversation', () => {
	beforeEach(() => {
		// Asking is only offered while something is there to answer
		review = openReview({ files: [file], facts: { answerer_attached: true } });
	});

	it('asks from the composer, where the comment is written', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();

		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(screen.getByRole('button', { name: 'Comment on line 2' }));
		await user.type(getByTestId('comment-input'), 'Where did 2 go?');
		await user.click(getByTestId('ask-now'));

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{
				thread: {
					body: 'Where did 2 go?',
					anchor: { quote: ['const y = 3;'], side: 'new', start_line: 2 }
				}
			}
		]);
	});

	it('marks a comment asked about as a question', async () => {
		const user = userEvent.setup({ delay: null });
		answering();

		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(screen.getByRole('button', { name: 'Comment on line 2' }));
		await user.type(getByTestId('comment-input'), 'Where did 2 go?');
		await user.click(getByTestId('ask-now'));

		expect(getByTestId('comment-severity').textContent).toContain('question');
	});

	it('says it is waiting rather than looking like nothing happened', async () => {
		const user = userEvent.setup({ delay: null });
		answering();
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));

		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('says, once the agent stops listening, what the panel says of a message it left unanswered', async () => {
		const user = userEvent.setup({ delay: null });
		answering();
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));

		review.answerer.setAttached(false);
		flushSync();

		const row = getByTestId('awaiting-answer').textContent;
		expect(row).toContain(AGENT_STOPPED_LISTENING);
		expect(row).not.toContain('the answer lands here');
	});

	it('takes back a question still waited on, as a panel message is taken back', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();
		server.answer('POST /api/cancel', null);
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));
		await user.click(getByTestId('awaiting-answer-take-back'));

		await user.click(getByTestId('confirm-go-ahead'));

		expect(server.bodiesSentTo('POST /api/cancel')).toEqual([{ message_id: id }]);
		expect(queryByTestId('awaiting-answer')).toBeNull();
		expect(getByTestId('ask-now-thread')).toBeTruthy();
	});

	it('says under a question taken back that it was, and when, and leaves the keyboard on the thread', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();
		server.answer('POST /api/cancel', null);
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));
		await user.click(getByTestId('awaiting-answer-take-back'));

		await user.keyboard('{Tab}{Enter}');
		await tick();

		expect(getByTestId('thread-taken-back').textContent).toContain(
			'Taken back 0s ago. The agent was asked to drop it.'
		);
		expect(document.activeElement).toBe(getByTestId('comment-thread'));
	});

	it('strikes a question no longer once it is asked again', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();
		server.answer('POST /api/cancel', null);
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));
		await user.click(getByTestId('awaiting-answer-take-back'));
		await user.click(getByTestId('confirm-go-ahead'));

		await user.click(getByTestId('ask-now-thread'));

		expect(queryByTestId('thread-taken-back')).toBeNull();
		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('leaves the keyboard on the thread once Ask agent now hands it over and goes', async () => {
		const user = userEvent.setup({ delay: null });
		answering();
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId } = render(DiffView, inReview(review));
		getByTestId('ask-now-thread').focus();

		await user.keyboard('{Enter}');
		await tick();

		expect(document.activeElement).toBe(getByTestId('comment-thread'));
	});

	it('says no round on a thread the agent raised, which never went out with one', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.raise('raised-1', anchor, 'Kept the old name on purpose', 'question');

		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		expect(getByTestId('thread-bar')).toBeTruthy();
		expect(queryByTestId('comment-sent')).toBeNull();
	});

	it("offers Ask agent now at the head of the reader's last turn, and at no other", () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });

		const { getAllByTestId } = render(DiffView, inReview(review));
		const [first, last] = getAllByTestId('thread-question');

		expect(within(first).queryByTestId('ask-now-thread')).toBeNull();
		expect(said(within(last).getByTestId('ask-now-thread'))).toBe('Ask agent now');
	});

	it('says where Ask agent now would stand that nobody is listening, and where what was written goes', () => {
		review.answerer.setAttached(false);
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView, inReview(review));

		expect(said(within(getByTestId('thread-question')).getByTestId('ask-hint'))).toBe(
			'No agent listening: this goes with the next round'
		);
	});

	it('keeps waiting on a question that could not be taken back, and says why', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();
		server.fail('POST /api/cancel', SERVER_ERROR);
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, findByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));
		await user.click(getByTestId('awaiting-answer-take-back'));

		await user.click(getByTestId('confirm-go-ahead'));

		// In the words of the button that was pressed, and the button still there to try again
		expect((await findByTestId('awaiting-answer-take-back-error')).textContent).toContain('Could not take it back');
		expect(getByTestId('awaiting-answer')).toBeTruthy();
		expect(getByTestId('awaiting-answer-take-back')).toBeTruthy();
	});

	it('offers no Ask agent now in a reply while the review cannot be reached, as a new comment offers none', async () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.writing.openReply(id);
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));
		expect(getByTestId('ask-now')).toBeTruthy();

		review.link.lost();
		flushSync();

		expect(queryByTestId('ask-now')).toBeNull();
	});

	it('shows the answer in the thread it belongs to', async () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		const { getByTestId, rerender } = render(DiffView, inReview(review));
		review.threads.receiveReply(id, 'It moved into the config default', null);
		await rerender({});

		expect(getByTestId('thread-answer').textContent).toContain('It moved into the config default');
	});

	it('marks a thread with an answer nobody has looked at', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		review.threads.receiveReply(id, 'It moved into the config default', null);

		expect(review.threads.unread.length).toBe(1);
		review.threads.reading.markRead(id);
		expect(review.threads.unread.length).toBe(0);
	});

	it('takes as new only the answers that arrived since the reader last looked', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.reading.markRead(id);
		review.threads.addTurn(id, { author: 'reader', body: 'Then say so in the docstring', images: [] });
		review.threads.receiveReply(id, 'Added', null);

		const [read, , arrived] = review.threads.all[0].turns;

		expect(arrivedSinceLooked(id, [read, arrived])).toEqual([false, true]);
	});

	it('takes every answer that arrived while the reader was away as new, and none once they look', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.addTurn(id, { author: 'reader', body: 'And why here?', images: [] });
		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.receiveReply(id, 'And here because the caller retries', null);
		const [, first, second] = review.threads.all[0].turns;
		expect(arrivedSinceLooked(id, [first, second])).toEqual([true, true]);

		review.threads.reading.markRead(id);

		expect(arrivedSinceLooked(id, [first, second])).toEqual([false, false]);
	});

	it('says a folded thread in its first words, plainly, and counts the replies under it', () => {
		const id = review.threads.add(onTheAddedLine('**Rename** `y`:\n\n```suggestion\nconst limit = 3;\n```'));
		review.threads.receiveReply(id, 'Done', null);
		review.threads.reading.setFolded(id, true);

		const { getByTestId } = render(DiffView, inReview(review));
		const folded = getByTestId('folded-thread').textContent?.replace(/\s+/g, ' ');

		expect(folded).toContain('Rename y: (a suggested change)');
		expect(folded).toContain('1 reply');
		expect(folded).not.toContain('**');
	});

	it('reads an answer the keyboard comes to, as one the mouse clicks on', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'It moved into the config default', null);
		const { getByTestId } = render(DiffView, inReview(review));

		getByTestId('resolve-comment').focus();

		expect(review.threads.unread).toHaveLength(0);
	});

	it('offers no menu on a thread the agent raised: the reader answers its words and settles it, never rewrites or deletes it', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.raise('raised-1', anchor, 'Kept the old name on purpose', 'note');
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('comment-thread')).toHaveLength(2);
		expect(getAllByTestId('thread-menu')).toHaveLength(1);
		expect(getAllByTestId('open-reply')).toHaveLength(2);
		expect(getAllByTestId('resolve-comment')).toHaveLength(2);
	});

	it('opens a thread the agent raised with the agent speaking', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.raise('raised-1', anchor, 'Kept the old name on purpose', 'note');

		const { getByTestId } = render(DiffView, inReview(review));

		expect(said(getByTestId('thread-question'))).toMatch(/^Agent /);
	});

	it('offers a reply in a field that reads "Reply…"', () => {
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView, inReview(review));

		expect(said(getByTestId('open-reply'))).toBe('Reply…');
	});

	it('asks, from its menu, before a thread is deleted, and deletes it only on yes', async () => {
		const user = userEvent.setup({ delay: null });
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		await user.click(getByTestId('thread-menu'));
		await user.click(getByTestId('delete-comment'));
		expect(getByTestId('delete-dialog-question').textContent).toBe('Delete this comment?');
		await user.click(getByTestId('confirm-keep'));
		expect(review.threads.count).toBe(1);
		expect(queryByTestId('delete-dialog-question')).toBeNull();

		await user.click(getByTestId('thread-menu'));
		await user.click(getByTestId('delete-comment'));
		await user.click(getByTestId('confirm-go-ahead'));
		expect(review.threads.count).toBe(0);
	});

	it('names, in the question before a thread is deleted, the replies that go with it', async () => {
		const user = userEvent.setup({ delay: null });
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'It moved into the config default', null);
		review.threads.receiveReply(id, 'And the old one is gone', null);
		const { getByTestId } = render(DiffView, inReview(review));

		await user.click(getByTestId('thread-menu'));
		await user.click(getByTestId('delete-comment'));

		expect(getByTestId('delete-dialog-question').textContent).toBe('Delete this comment and its 2 replies?');
	});

	it('opens the comment to be rewritten, from its menu', async () => {
		const user = userEvent.setup({ delay: null });
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId } = render(DiffView, inReview(review));

		await user.click(getByTestId('thread-menu'));
		await user.click(getByTestId('edit-comment'));

		expect((getByTestId('comment-input') as HTMLTextAreaElement).value).toBe('Why 3?');
	});

	it('keeps every turn rather than overwriting the last one', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.addTurn(id, { author: 'reader', body: 'Then say so in the docstring', images: [] });
		review.threads.receiveReply(id, 'Added', null);

		expect(review.threads.all[0].turns.map((turn) => turn.author)).toEqual(['author', 'reader', 'author']);
	});

	it('does not offer to ask while the review cannot be reached', () => {
		review.link.lost();
		review.threads.add(onTheAddedLine('Why 3?'));

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('ask-now-thread')).toBeNull();
	});

	it('does not offer to ask when nothing is there to answer', async () => {
		// Nobody attached: the review can only be sent whole
		review.answerer.setAttached(false);
		review.threads.add(onTheAddedLine('Why 3?'));

		const { queryByTestId } = render(DiffView, inReview(review));

		expect(queryByTestId('ask-now-thread')).toBeNull();
	});

	it('puts an answer under the question it answers, not under the last one', async () => {
		answering();
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		await review.threads.ask(id);
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		await review.threads.ask(id);

		// The first answer arrives after the second question was already asked
		review.threads.receiveReply(id, 'Because of the retry path', null);

		const answer = review.threads.all[0].turns.find((turn) => turn.author === 'author');
		expect(answer?.answers).toBe(id);
		expect(review.threads.reading.awaiting(review.threads.all[0].id)).toHaveLength(1);
	});

	it('believes an answer that names its question', async () => {
		answering();
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		await review.threads.ask(id);
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		await review.threads.ask(id);
		const second = review.threads.reading.awaiting(review.threads.all[0].id)[1].id;

		review.threads.receiveReply(id, 'Into the config default', second);

		expect(review.threads.all[0].turns.at(-1)?.answers).toBe(second);
		expect(review.threads.reading.awaiting(review.threads.all[0].id).map((waiting) => waiting.id)).toEqual([id]);
	});

	it('hands over the comment that opened the thread, not only the replies', async () => {
		const server = answering();
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });

		await review.threads.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { body: 'Why 3?', turns: [{ body: 'And where did 2 go?' }] } }
		]);
	});

	it('names the reply it asks when the reader said the last word', async () => {
		const server = answering();
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		const reply = review.threads.all[0].turns[1].id;

		await review.threads.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([{ question_id: reply }]);
		expect(review.threads.reading.awaiting(review.threads.all[0].id).map((waiting) => waiting.id)).toEqual([reply]);
	});

	it('names the thread itself when the agent said the last word', async () => {
		const server = answering();
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'Because of the retry path', null);

		await review.threads.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([{ question_id: id }]);
	});

	it('renders what an answer wrote as markdown', async () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		const { getAllByTestId, rerender } = render(DiffView, inReview(review));
		review.threads.receiveReply(id, 'Look at\n\n```python\nreturn 1\n```', null);
		await rerender({});

		const rendered = getAllByTestId('markdown-content').at(-1);
		expect(rendered?.querySelector('pre code')).toBeTruthy();
	});

	it('does not leave a thread waiting when the question could not be sent', async () => {
		const user = userEvent.setup({ delay: null });
		fakeServer().refuse('POST /api/ask', SERVER_ERROR);
		review.threads.add(onTheAddedLine('Why 3?'));

		const { findByTestId, getByTestId, queryByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));

		// The refusal is read off the server's answer before it is shown, under the words it was asked about
		const failure = await findByTestId('ask-error');
		expect(getByTestId('thread-question').contains(failure)).toBe(true);
		expect(queryByTestId('awaiting-answer')).toBeNull();
		expect(getByTestId('ask-now-thread')).toBeTruthy();
	});

	it('keeps saying why a question could not be sent once nothing is there to ask', async () => {
		const user = userEvent.setup({ delay: null });
		fakeServer().refuse('POST /api/ask', SERVER_ERROR);
		review.threads.add(onTheAddedLine('Why 3?'));
		const { findByTestId, getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));
		await findByTestId('ask-error');

		review.answerer.setAttached(false);
		flushSync();

		expect(getByTestId('ask-error')).toBeTruthy();
	});

	it('a settled thread gives back its space and says so on the way out', async () => {
		const user = userEvent.setup({ delay: null });
		const id = review.threads.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('resolve-comment'));

		expect(getByTestId('resolved-thread')).toBeTruthy();
		expect(review.threads.all[0].resolved).toBe(true);
		expect(id).toBe(review.threads.all[0].id);
	});
});

describe('the bar of a thread', () => {
	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	/** The review's first thread, drawn as the page draws it, under its line. */
	function firstThread() {
		return within(render(CommentThread, inReview(review, { thread: review.threads.all[0], hangs: 'line' })).container);
	}

	it('says what the thread asks for, that it is outdated, and the round it went out in', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.add({ ...onTheAddedLine('Why 3?'), severity: 'question', anchor: { ...anchor, outdated: true } });
		review.threads.markSent(review.threads.carry(review.threads.all), 1);

		const bar = within(firstThread().getByTestId('thread-bar'));

		expect(said(bar.getByTestId('comment-severity'))).toBe('question');
		expect(bar.getByTestId('comment-outdated')).toBeTruthy();
		expect(said(bar.getByTestId('comment-sent'))).toBe('sent in round 1');
	});

	it('says, folded, that the agent is answering and that a reply is new, and no longer the round it went out in', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.markSent(review.threads.carry(review.threads.all), 1);
		review.threads.receiveReply(id, 'It moved into the config default', null);
		review.threads.reading.asked(id, 'turn-asked');
		review.threads.reading.setFolded(id, true);

		const bar = within(firstThread().getByTestId('thread-bar'));

		expect(said(bar.getByTestId('comment-answering'))).toBe('answering');
		expect(said(bar.getByTestId('comment-unread'))).toBe('new reply');
		expect(bar.queryByTestId('comment-sent')).toBeNull();
	});
});

describe('images in a thread', () => {
	beforeEach(() => {
		review = openReview({ files: [file], facts: { answerer_attached: true } });
	});

	it('hands the agent the images of the question and of everything said before it', async () => {
		const server = answering();
		const id = review.threads.add(onTheAddedLine('Looks off', ['opening.png']));
		review.threads.addTurn(id, { author: 'reader', body: 'Here it is again', images: ['reply.png'] });

		await review.threads.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { images: ['opening.png'], turns: [{ images: ['reply.png'] }] } }
		]);
	});

	it('draws the images of the comment and of each reply', () => {
		const id = review.threads.add(onTheAddedLine('Looks off', ['opening.png']));
		review.threads.addTurn(id, { author: 'reader', body: 'Here it is again', images: ['reply.png'] });

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('said-image').map((link) => link.getAttribute('href'))).toEqual([
			'/api/images/opening.png',
			'/api/images/reply.png'
		]);
	});
});
