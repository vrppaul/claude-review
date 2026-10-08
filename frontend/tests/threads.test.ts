import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import { addedLine, contextLine, diffFile, hunk } from './diff';
import { fakeServer, SERVER_ERROR, type FakeServer } from './fake-server';
import { newComment } from './new-comment';

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
		reviewStore.attachAnswerer();
		diffStore.setFiles([file], 'diff');
	});

	it('asks from the composer, where the comment is written', async () => {
		const user = userEvent.setup({ delay: null });
		const server = answering();

		const { getByTestId, getAllByTestId } = render(DiffView);
		await user.click(getAllByTestId('line-gutter')[1]);
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

		const { getByTestId, getAllByTestId } = render(DiffView);
		await user.click(getAllByTestId('line-gutter')[1]);
		await user.type(getByTestId('comment-input'), 'Where did 2 go?');
		await user.click(getByTestId('ask-now'));

		expect(getByTestId('comment-severity').textContent).toContain('question');
	});

	it('says it is waiting rather than looking like nothing happened', async () => {
		const user = userEvent.setup({ delay: null });
		answering();
		commentStore.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('ask-now-thread'));

		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('shows the answer in the thread it belongs to', async () => {
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		const { getByTestId, rerender } = render(DiffView);
		commentStore.receiveReply(id, 'It moved into the config default');
		await rerender({});

		expect(getByTestId('thread-answer').textContent).toContain('It moved into the config default');
	});

	it('marks a thread with an answer nobody has looked at', () => {
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		commentStore.receiveReply(id, 'It moved into the config default');

		expect(commentStore.unreadCount).toBe(1);
		commentStore.markRead(id);
		expect(commentStore.unreadCount).toBe(0);
	});

	it('keeps every turn rather than overwriting the last one', () => {
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		commentStore.receiveReply(id, 'Because of the retry path');
		commentStore.addTurn(id, { author: 'reader', body: 'Then say so in the docstring', images: [] });
		commentStore.receiveReply(id, 'Added');

		expect(commentStore.comments[0].turns.map((turn) => turn.author)).toEqual([
			'author',
			'reader',
			'author'
		]);
	});

	it('does not offer to ask when nothing is there to answer', async () => {
		// Nobody attached: the review can only be sent whole
		reviewStore.clear();
		commentStore.add(onTheAddedLine('Why 3?'));

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('ask-now-thread')).toBeNull();
	});

	it('puts an answer under the question it answers, not under the last one', async () => {
		answering();
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		await commentStore.ask(id);
		commentStore.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		await commentStore.ask(id);

		// The first answer arrives after the second question was already asked
		commentStore.receiveReply(id, 'Because of the retry path');

		const answer = commentStore.comments[0].turns.find((turn) => turn.author === 'author');
		expect(answer?.answers).toBe(id);
		expect(commentStore.comments[0].awaiting).toHaveLength(1);
	});

	it('believes an answer that names its question', async () => {
		answering();
		const id = commentStore.add(onTheAddedLine('Why 3?'));
		await commentStore.ask(id);
		commentStore.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		await commentStore.ask(id);
		const second = commentStore.comments[0].awaiting[1].id;

		commentStore.receiveReply(id, 'Into the config default', second);

		expect(commentStore.comments[0].turns.at(-1)?.answers).toBe(second);
		expect(commentStore.comments[0].awaiting.map((waiting) => waiting.id)).toEqual([id]);
	});

	it('hands over the comment that opened the thread, not only the replies', async () => {
		const server = answering();
		const id = commentStore.add(onTheAddedLine('Why 3?'));
		commentStore.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });

		await commentStore.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { body: 'Why 3?', turns: [{ body: 'And where did 2 go?' }] } }
		]);
	});

	it('names the reply it asks when the reader said the last word', async () => {
		const server = answering();
		const id = commentStore.add(onTheAddedLine('Why 3?'));
		commentStore.receiveReply(id, 'Because of the retry path');
		commentStore.addTurn(id, { author: 'reader', body: 'And where did 2 go?', images: [] });
		const reply = commentStore.comments[0].turns[1].id;

		await commentStore.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([{ question_id: reply }]);
		expect(commentStore.comments[0].awaiting.map((waiting) => waiting.id)).toEqual([reply]);
	});

	it('names the thread itself when the agent said the last word', async () => {
		const server = answering();
		const id = commentStore.add(onTheAddedLine('Why 3?'));
		commentStore.receiveReply(id, 'Because of the retry path');

		await commentStore.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([{ question_id: id }]);
	});

	it('renders what an answer wrote as markdown', async () => {
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		const { getAllByTestId, rerender } = render(DiffView);
		commentStore.receiveReply(id, 'Look at\n\n```python\nreturn 1\n```');
		await rerender({});

		const rendered = getAllByTestId('markdown-content').at(-1);
		expect(rendered?.querySelector('pre code')).toBeTruthy();
	});

	it('does not leave a thread waiting when the question could not be sent', async () => {
		const user = userEvent.setup({ delay: null });
		fakeServer().refuse('POST /api/ask', SERVER_ERROR);
		commentStore.add(onTheAddedLine('Why 3?'));

		const { getByTestId, queryByTestId } = render(DiffView);
		await user.click(getByTestId('ask-now-thread'));

		expect(getByTestId('ask-error')).toBeTruthy();
		expect(queryByTestId('awaiting-answer')).toBeNull();
	});

	it('a settled thread gives back its space and says so on the way out', async () => {
		const user = userEvent.setup({ delay: null });
		const id = commentStore.add(onTheAddedLine('Why 3?'));

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('resolve-comment'));

		expect(getByTestId('resolved-thread')).toBeTruthy();
		expect(commentStore.comments[0].resolved).toBe(true);
		expect(id).toBe(commentStore.comments[0].id);
	});
});

describe('images in a thread', () => {
	beforeEach(() => {
		reviewStore.attachAnswerer();
		diffStore.setFiles([file], 'diff');
	});

	it('hands the agent the images of the question and of everything said before it', async () => {
		const server = answering();
		const id = commentStore.add(onTheAddedLine('Looks off', ['opening.png']));
		commentStore.addTurn(id, { author: 'reader', body: 'Here it is again', images: ['reply.png'] });

		await commentStore.ask(id);

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { images: ['opening.png'], turns: [{ images: ['reply.png'] }] } }
		]);
	});

	it('draws the images of the comment and of each reply', () => {
		const id = commentStore.add(onTheAddedLine('Looks off', ['opening.png']));
		commentStore.addTurn(id, { author: 'reader', body: 'Here it is again', images: ['reply.png'] });

		const { getAllByTestId } = render(DiffView);

		expect(getAllByTestId('said-image').map((link) => link.getAttribute('href'))).toEqual([
			'/api/images/opening.png',
			'/api/images/reply.png'
		]);
	});
});
