import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import AgentPanel from '$lib/components/AgentPanel.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { panelStore } from '$lib/stores/panel.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
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
			lines: [{ type: 'add', old_no: null, new_no: 2, content: 'y = 3' }]
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

describe('the agent panel', () => {
	beforeEach(() => {
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
		reviewStore.clear();
		panelStore.clear();
		diffStore.setFiles([file], 'diff', TITLE);
		commentStore.restore(TITLE);
		panelStore.restore(TITLE);
		reviewStore.attachAnswerer();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('says what it is for before anything has been said', () => {
		const { getByTestId } = render(AgentPanel);

		expect(getByTestId('panel-empty')).toBeTruthy();
		expect(getByTestId('panel-input')).toBeTruthy();
	});

	it('offers nothing to type into when nobody is listening', () => {
		reviewStore.clear();

		const { getByTestId, queryByTestId } = render(AgentPanel);

		expect(getByTestId('panel-unattached')).toBeTruthy();
		expect(getByTestId('panel-read-only')).toBeTruthy();
		expect(queryByTestId('panel-input')).toBeNull();
	});

	it('sends what was typed and empties the field', async () => {
		const user = userEvent.setup({ delay: null });
		const fetchMock = okFetch();

		const { getByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Run the tests');
		await user.click(getByTestId('send-message'));

		expect(JSON.parse(fetchMock.mock.calls[0][1].body).text).toBe('Run the tests');
		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe('');
	});

	it('points at a thread by picking it, not by retyping which line it was', async () => {
		const user = userEvent.setup({ delay: null });
		okFetch();
		commentStore.add('src/routes.py', 'new', 2, 2, 'Why catch here?');

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Look at @');
		await user.click(getAllByTestId('thread-option')[0]);

		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe(
			'Look at @src/routes.py:2-2 '
		);
		expect(getByTestId('pointed-thread').textContent).toContain('routes.py');
	});

	it('sends the thread the message points at', async () => {
		const user = userEvent.setup({ delay: null });
		const fetchMock = okFetch();
		commentStore.add('src/routes.py', 'new', 2, 2, 'Why catch here?');

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Look at @');
		await user.click(getAllByTestId('thread-option')[0]);
		await user.type(getByTestId('panel-input'), 'again');
		await user.click(getByTestId('send-message'));

		const body = JSON.parse(fetchMock.mock.calls[0][1].body);
		expect(body.threads).toHaveLength(1);
		expect(body.threads[0].body).toBe('Why catch here?');
	});

	it('offers to stop a message the agent is still working on', async () => {
		const user = userEvent.setup({ delay: null });
		const fetchMock = okFetch();

		const { getByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Never mind');
		await user.click(getByTestId('send-message'));

		expect(getByTestId('panel-working')).toBeTruthy();
		await user.click(getByTestId('stop-message'));

		expect(fetchMock.mock.calls[1][0]).toBe('/api/cancel');
		expect(getByTestId('panel-cancelled')).toBeTruthy();
	});

	/** jsdom lays nothing out, so the panel is given a height to scroll in. */
	function givenTall(element: HTMLElement, { visible = 100, total = 500 } = {}) {
		Object.defineProperty(element, 'clientHeight', { value: visible, configurable: true });
		Object.defineProperty(element, 'scrollHeight', { value: total, configurable: true });
	}

	function painted(): Promise<void> {
		return new Promise((resolve) => requestAnimationFrame(() => resolve()));
	}

	it('brings a new turn into view', async () => {
		okFetch();
		const { getByTestId } = render(AgentPanel);
		const stream = getByTestId('panel-turns');
		givenTall(stream);

		await panelStore.send('Run the tests', []);
		panelStore.receive(panelStore.turns[0].id, 'One failed; fixed and green.');
		await painted();

		expect(stream.scrollTop).toBe(500);
	});

	it('leaves the reader where they are reading', async () => {
		okFetch();
		await panelStore.send('Run the tests', []);

		const { getByTestId } = render(AgentPanel);
		const stream = getByTestId('panel-turns');
		givenTall(stream);
		// Scrolled up into what was said earlier
		stream.scrollTop = 0;
		stream.dispatchEvent(new Event('scroll'));

		panelStore.receive(panelStore.turns[0].id, 'One failed; fixed and green.');
		await painted();

		expect(stream.scrollTop).toBe(0);
	});

	it('tells the review it can weigh apart from the context only the agent knows', () => {
		panelStore.report({ model: 'opus-5', context: '53% of 1M', at: Date.now() });

		const { getByTestId } = render(AgentPanel);

		expect(getByTestId('review-weight').textContent).toContain('review ~');
		expect(getByTestId('agent-context').textContent).toContain('53% of 1M');
		expect(getByTestId('agent-context').textContent).toContain('as reported');
		expect(getByTestId('agent-model').textContent).toContain('opus-5');
	});

	it('shows no context at all rather than a number nobody reported', () => {
		const { queryByTestId, getByTestId } = render(AgentPanel);

		expect(getByTestId('review-weight')).toBeTruthy();
		expect(queryByTestId('agent-context')).toBeNull();
	});
});
