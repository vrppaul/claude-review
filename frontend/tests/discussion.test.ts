import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { discussionStore } from '$lib/stores/discussion.svelte';
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

describe('asking Claude about a thread', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
		discussionStore.clear();
		localStorage.clear();
		diffStore.setFiles([file], 'diff');
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('sends the question with the lines it is about', async () => {
		const user = userEvent.setup();
		const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
		vi.stubGlobal('fetch', fetchMock);
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('ask-claude'));
		await user.type(getByTestId('ask-input'), 'Where did 2 go?');
		await user.click(getByTestId('send-question'));

		const body = JSON.parse(fetchMock.mock.calls[0][1].body);
		expect(body.body).toBe('Where did 2 go?');
		expect(body.quote).toEqual(['const y = 3;']);
		expect(body.side).toBe('new');
		expect(body.start_line).toBe(2);
	});

	it('says it is waiting rather than looking like nothing happened', async () => {
		const user = userEvent.setup();
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId } = render(DiffView);
		await user.click(getByTestId('ask-claude'));
		await user.type(getByTestId('ask-input'), 'Where did 2 go?');
		await user.click(getByTestId('send-question'));

		expect(getByTestId('awaiting-answer')).toBeTruthy();
	});

	it('shows the answer in the thread it belongs to', async () => {
		const user = userEvent.setup();
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
		const id = commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId, rerender } = render(DiffView);
		await user.click(getByTestId('ask-claude'));
		await user.type(getByTestId('ask-input'), 'Where did 2 go?');
		await user.click(getByTestId('send-question'));

		discussionStore.receive(id, 'It moved into the config default');
		await rerender({});

		expect(getByTestId('thread-answer').textContent?.trim()).toBe(
			'It moved into the config default'
		);
	});

	it('does not leave a thread waiting when the question could not be sent', async () => {
		const user = userEvent.setup();
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
		commentStore.add('src/handler.ts', 'new', 2, 2, 'Why 3?');

		const { getByTestId, queryByTestId } = render(DiffView);
		await user.click(getByTestId('ask-claude'));
		await user.type(getByTestId('ask-input'), 'Where did 2 go?');
		await user.click(getByTestId('send-question'));

		expect(getByTestId('ask-error')).toBeTruthy();
		expect(queryByTestId('awaiting-answer')).toBeNull();
	});
});
