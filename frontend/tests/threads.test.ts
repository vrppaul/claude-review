import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import type { DiffFile } from '$lib/types';

const file: DiffFile = {
	path: 'src/handler.ts',
	status: 'modified',
	hunks: [
		{
			header: '@@ -1,2 +1,2 @@',
			old_start: 1,
			new_start: 1,
			lines: [
				{ type: 'context', old_no: 1, new_no: 1, content: 'const x = 1;' },
				{ type: 'add', old_no: null, new_no: 2, content: 'const y = 3;' }
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

describe('a thread is a conversation', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		reviewStore.clear();
		// Asking is only offered while something is there to answer
		reviewStore.attachAnswerer();
		localStorage.clear();
		diffStore.setFiles([file], 'diff');
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('asks from the composer, where the comment is written', async () => {
		const user = userEvent.setup({ delay: null });
		const fetchMock = okFetch();

		const { getByTestId, getAllByTestId } = render(DiffView);
		await user.click(getAllByTestId('line-gutter')[1]);
		await user.type(getByTestId('comment-input'), 'Where did 2 go?');
		await user.click(getByTestId('ask-now'));

		const asked = JSON.parse(fetchMock.mock.calls[0][1].body);
		expect(asked.body).toBe('Where did 2 go?');
		expect(asked.quote).toEqual(['const y = 3;']);
		expect(asked.side).toBe('new');
		expect(asked.start_line).toBe(2);
	});

	it('marks a comment asked about as a question', async () => {
		const user = userEvent.setup({ delay: null });
		okFetch();

		const { getByTestId, getAllByTestId } = render(DiffView);
		await user.click(getAllByTestId('line-gutter')[1]);
		await user.type(getByTestId('comment-input'), 'Where did 2 go?');
		await user.click(getByTestId('ask-now'));

		expect(commentStore.comments[0].severity).toBe('question');
	});

	it('says it is waiting rather than looking like nothing happened', async () => {
		const user = userEvent.setup({ delay: null });
		okFetch();
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?', 'note', ['const y = 3;']);

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('ask-now-thread'));

		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('shows the answer in the thread it belongs to', async () => {
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId, rerender } = render(DiffView);
		commentStore.receiveReply(id, 'It moved into the config default');
		await rerender({});

		expect(getByTestId('thread-answer').textContent).toContain('It moved into the config default');
	});

	it('marks a thread with an answer nobody has looked at', () => {
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		commentStore.receiveReply(id, 'It moved into the config default');

		expect(commentStore.unreadCount).toBe(1);
		commentStore.markRead(id);
		expect(commentStore.unreadCount).toBe(0);
	});

	it('keeps every turn rather than overwriting the last one', () => {
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		commentStore.receiveReply(id, 'Because of the retry path');
		commentStore.addTurn(id, 'reader', 'Then say so in the docstring');
		commentStore.receiveReply(id, 'Added');

		expect(commentStore.comments[0].turns.map((t) => t.author)).toEqual([
			'author',
			'reader',
			'author'
		]);
	});

	it('does not offer to ask when nothing is there to answer', async () => {
		reviewStore.clear();
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { queryByTestId } = render(DiffView);

		expect(queryByTestId('ask-now-thread')).toBeNull();
	});

	it('puts an answer under the question it answers, not under the last one', async () => {
		okFetch();
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		await commentStore.ask(id);
		commentStore.addTurn(id, 'reader', 'And where did 2 go?');
		await commentStore.ask(id);

		// The first answer arrives after the second question was already asked
		commentStore.receiveReply(id, 'Because of the retry path');

		const answer = commentStore.comments[0].turns.find((t) => t.author === 'author');
		expect(answer?.answers).toBe(id);
		expect(commentStore.comments[0].awaiting).toHaveLength(1);
	});

	it('believes an answer that names its question', async () => {
		okFetch();
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');
		await commentStore.ask(id);
		commentStore.addTurn(id, 'reader', 'And where did 2 go?');
		await commentStore.ask(id);
		const second = commentStore.comments[0].awaiting[1].id;

		commentStore.receiveReply(id, 'Into the config default', second);

		expect(commentStore.comments[0].turns.at(-1)?.answers).toBe(second);
		expect(commentStore.comments[0].awaiting.map((w) => w.id)).toEqual([id]);
	});

	it('hands over the comment that opened the thread, not only the replies', async () => {
		const fetchMock = okFetch();
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');
		commentStore.addTurn(id, 'reader', 'And where did 2 go?');

		await commentStore.ask(id);

		const asked = JSON.parse(fetchMock.mock.calls[0][1].body);
		expect(asked.body).toBe('And where did 2 go?');
		expect(asked.history.map((t: { body: string }) => t.body)).toEqual(['Why 3?']);
	});

	it('renders what an answer wrote as markdown', async () => {
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getAllByTestId, rerender } = render(DiffView);
		commentStore.receiveReply(id, 'Look at\n\n```python\nreturn 1\n```');
		await rerender({});

		const rendered = getAllByTestId('markdown-content').at(-1);
		expect(rendered?.querySelector('pre code')).toBeTruthy();
	});

	it('does not leave a thread waiting when the question could not be sent', async () => {
		const user = userEvent.setup({ delay: null });
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId, queryByTestId } = render(DiffView);
		await user.click(getByTestId('ask-now-thread'));

		expect(getByTestId('ask-error')).toBeTruthy();
		expect(queryByTestId('awaiting-answer')).toBeNull();
	});

	it('a settled thread gives back its space and says so on the way out', async () => {
		const user = userEvent.setup({ delay: null });
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('resolve-comment'));

		expect(getByTestId('resolved-thread')).toBeTruthy();
		expect(commentStore.comments[0].resolved).toBe(true);
		expect(id).toBe(commentStore.comments[0].id);
	});
});
