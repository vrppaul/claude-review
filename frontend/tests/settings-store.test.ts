import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { settingsStore } from '$lib/stores/settings.svelte';
import type { ReaderSettings } from '$lib/types';

const NEW_READER: ReaderSettings = {
	theme: 'system',
	diff_layout: 'unified',
	ignore_whitespace: false,
	sound_on_replies: false
};

/** A server holding these settings, or none, answering a read and echoing a change. */
function serving(settings: ReaderSettings, stored: boolean) {
	const mock = vi.fn().mockImplementation((_url: string, init?: RequestInit) =>
		Promise.resolve({
			ok: true,
			json: () =>
				Promise.resolve(
					init?.method === 'PUT'
						? { ...settings, ...JSON.parse(String(init.body)) }
						: { settings, stored }
				)
		})
	);
	vi.stubGlobal('fetch', mock);
	return mock;
}

function changesSent(mock: ReturnType<typeof vi.fn>): unknown[] {
	return mock.mock.calls
		.filter(([, init]) => (init as RequestInit | undefined)?.method === 'PUT')
		.map(([, init]) => JSON.parse(String((init as RequestInit).body)));
}

describe('the reader settings', () => {
	beforeEach(() => {
		localStorage.clear();
		settingsStore.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('come from the server, the same in every review', async () => {
		serving({ ...NEW_READER, diff_layout: 'split', theme: 'dark' }, true);

		await settingsStore.load();

		expect(settingsStore.settings.diff_layout).toBe('split');
		expect(settingsStore.settings.theme).toBe('dark');
	});

	it('take over what this browser kept before the server did, once', async () => {
		localStorage.setItem('claude-review:layout', 'split');
		localStorage.setItem('claude-review:reply-sound', 'on');
		const fetchMock = serving(NEW_READER, false);

		await settingsStore.load();

		expect(changesSent(fetchMock)).toEqual([
			{ theme: 'system', diff_layout: 'split', ignore_whitespace: false, sound_on_replies: true }
		]);
		expect(settingsStore.settings.diff_layout).toBe('split');
		// Dropped, so another review does not hand over stale copies later
		expect(localStorage.getItem('claude-review:layout')).toBeNull();
		expect(localStorage.getItem('claude-review:reply-sound')).toBeNull();
	});

	it('leave out a choice this browser kept that is no longer a choice', async () => {
		localStorage.setItem('claude-review:layout', 'three-columns');
		localStorage.setItem('claude-review:ignore-whitespace', 'on');
		const fetchMock = serving(NEW_READER, false);

		await settingsStore.load();

		expect(changesSent(fetchMock)).toEqual([{ ...NEW_READER, ignore_whitespace: true }]);
	});

	it('hand nothing over when this browser kept nothing', async () => {
		const fetchMock = serving(NEW_READER, false);

		await settingsStore.load();

		expect(changesSent(fetchMock)).toEqual([]);
	});

	it('take nothing over once the server has settings of its own', async () => {
		localStorage.setItem('claude-review:layout', 'split');
		const fetchMock = serving(NEW_READER, true);

		await settingsStore.load();

		expect(changesSent(fetchMock)).toEqual([]);
		expect(settingsStore.settings.diff_layout).toBe('unified');
	});

	it('apply a change at once and send only what changed', async () => {
		const fetchMock = serving(NEW_READER, true);

		await settingsStore.change({ ignore_whitespace: true });

		expect(settingsStore.settings.ignore_whitespace).toBe(true);
		expect(changesSent(fetchMock)).toEqual([{ ignore_whitespace: true }]);
	});

	it('keep reading with what the tab has when the server cannot say', async () => {
		vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('gone')));

		await settingsStore.load();
		await settingsStore.change({ diff_layout: 'split' });

		expect(settingsStore.settings.diff_layout).toBe('split');
	});
});
