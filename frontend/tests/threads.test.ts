import { describe, it, expect, beforeEach } from 'vitest';
import { flushSync } from 'svelte';
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

		await user.click(getByTestId('take-back-question'));

		expect(server.bodiesSentTo('POST /api/cancel')).toEqual([{ message_id: id }]);
		expect(queryByTestId('awaiting-answer')).toBeNull();
		expect(getByTestId('ask-now-thread')).toBeTruthy();
	});

	it('keeps waiting on a question that could not be taken back, and says why', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();
		server.fail('POST /api/cancel', SERVER_ERROR);
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, findByTestId } = render(DiffView, inReview(review));
		await user.click(getByTestId('ask-now-thread'));

		await user.click(getByTestId('take-back-question'));

		// In the words of the button that was pressed
		expect((await findByTestId('take-back-error')).textContent).toContain('Could not take it back');
		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('offers no Ask now in a reply while the review cannot be reached, as a new comment offers none', async () => {
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

	it('draws as new only the answers that arrived since the reader last looked', () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.reading.markRead(id);
		review.threads.addTurn(id, { author: 'reader', body: 'Then say so in the docstring', images: [] });
		review.threads.receiveReply(id, 'Added', null);

		const { getAllByTestId } = render(DiffView, inReview(review));
		const [read, unread] = getAllByTestId('thread-answer');

		expect(read.classList).not.toContain('cr-answer-new');
		expect(unread.classList).toContain('cr-answer-new');
	});

	it('draws every answer that arrived while the reader was away as new, and none once they look', async () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.addTurn(id, { author: 'reader', body: 'And why here?', images: [] });
		review.threads.receiveReply(id, 'Because of the retry path', null);
		review.threads.receiveReply(id, 'And here because the caller retries', null);

		const { getAllByTestId } = render(DiffView, inReview(review));
		const answers = getAllByTestId('thread-answer');
		expect(answers.map((answer) => answer.classList.contains('cr-answer-new'))).toEqual([true, true]);

		review.threads.reading.markRead(id);
		flushSync();
		expect(answers.map((answer) => answer.classList.contains('cr-answer-new'))).toEqual([false, false]);
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

		getByTestId('edit-comment').focus();

		expect(review.threads.unread).toHaveLength(0);
	});

	it('offers no edit of a thread the agent raised: the reader answers its words, never rewrites them', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.raise('raised-1', anchor, 'Kept the old name on purpose', 'note');
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('comment-thread')).toHaveLength(2);
		expect(getAllByTestId('edit-comment')).toHaveLength(1);
		expect(getAllByTestId('open-reply')).toHaveLength(2);
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

	it('offers no delete of a thread the agent raised, which the review keeps whatever a page says, but lets it be settled', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.raise('raised-1', anchor, 'Kept the old name on purpose', 'note');
		review.threads.add(onTheAddedLine('Why 3?'));

		const { getAllByTestId } = render(DiffView, inReview(review));

		expect(getAllByTestId('delete-comment')).toHaveLength(1);
		expect(getAllByTestId('resolve-comment')).toHaveLength(2);
	});

	it('asks before a thread is deleted, and deletes it only on yes', async () => {
		const user = userEvent.setup({ delay: null });
		review.threads.add(onTheAddedLine('Why 3?'));
		const { getByTestId, queryByTestId } = render(DiffView, inReview(review));

		await user.click(getByTestId('delete-comment'));
		expect(getByTestId('delete-dialog').textContent).toContain('Delete this comment?');
		await user.click(getByTestId('confirm-keep'));
		expect(review.threads.count).toBe(1);
		expect(queryByTestId('delete-dialog')).toBeNull();

		await user.click(getByTestId('delete-comment'));
		await user.click(getByTestId('confirm-go-ahead'));
		expect(review.threads.count).toBe(0);
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

		// The refusal is read off the server's answer before it is shown
		expect(await findByTestId('ask-error')).toBeTruthy();
		expect(queryByTestId('awaiting-answer')).toBeNull();
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

describe('the head of the first turn of a thread', () => {
	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	/** The first turn of the review's first thread, drawn open as the page draws it, under its line. */
	function firstTurn() {
		const { getByTestId } = render(CommentThread, inReview(review, { thread: review.threads.all[0], hangs: 'line' }));
		return getByTestId('thread-question');
	}

	it('holds what can be done to the thread: resolve, edit, delete and fold', () => {
		review.threads.add(onTheAddedLine('Why 3?'));

		const opening = within(firstTurn());

		expect(opening.getByTestId('resolve-comment')).toBeTruthy();
		expect(opening.getByRole('button', { name: 'Edit' })).toBe(opening.getByTestId('edit-comment'));
		expect(opening.getByRole('button', { name: 'Delete' })).toBe(opening.getByTestId('delete-comment'));
		expect(opening.getByTestId('fold-comment')).toBeTruthy();
	});

	it("is the first turn's alone: a question asked after it holds nothing to do to the thread", () => {
		const id = review.threads.add(onTheAddedLine('Why 3?'));
		review.threads.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });

		const { getAllByTestId } = render(
			CommentThread,
			inReview(review, { thread: review.threads.all[0], hangs: 'line' })
		);
		const [, second] = getAllByTestId('thread-question');

		expect(within(second).queryByTestId('resolve-comment')).toBeNull();
	});

	it('names the place the thread hangs on after how long ago it was said', () => {
		review.threads.add(onTheAddedLine('Why 3?'));

		expect(said(firstTurn())).toMatch(/^You \d+s ago \+ Line 2 /);
	});

	it('says what the thread asks for, that it is outdated, and the round it went out in', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.add({ ...onTheAddedLine('Why 3?'), severity: 'question', anchor: { ...anchor, outdated: true } });
		review.threads.markSent(review.threads.carry(review.threads.all), 1);

		const opening = within(firstTurn());

		expect(said(opening.getByTestId('comment-severity'))).toBe('question');
		expect(opening.getByTestId('comment-outdated')).toBeTruthy();
		expect(said(opening.getByTestId('comment-sent'))).toBe('sent · round 1');
	});

	it('is followed, on an outdated thread, by what it was written against, and then by its words', () => {
		const { anchor } = onTheAddedLine('');
		review.threads.add({ ...onTheAddedLine('Why 3?'), anchor: { ...anchor, outdated: true } });

		const opening = within(firstTurn());

		const words = opening.getByTestId('markdown-content');
		expect(opening.getByTestId('stale-quote').compareDocumentPosition(words)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
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
