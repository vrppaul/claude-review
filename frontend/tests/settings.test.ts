import { beforeEach, describe, it, expect } from 'vitest';
import { Settings } from '$lib/reader/settings.svelte';
import type { ReaderSettings } from '$lib/types';
import { fakeServer, keepingSettings, NEW_READER, SERVER_ERROR, type FakeServer } from './fake-server';

// The names this browser kept choices under before the server kept them.
// The theme's is also where the first paint reads it, before the server answers.
const THEME_KEPT_HERE = 'claude-review:theme';
const LAYOUT_KEPT_HERE = 'claude-review:layout';
const WHITESPACE_KEPT_HERE = 'claude-review:ignore-whitespace';
const SOUND_KEPT_HERE = 'claude-review:reply-sound';

// What this browser hands over of a reader who chose nothing here: the four choices it ever kept, and no other
const NOTHING_CHOSEN_HERE = {
	theme: 'system',
	diff_layout: 'unified',
	ignore_whitespace: false,
	sound_on_replies: false
};

/** A server holding these settings, or none, and taking every change on top of them. */
function serving(settings: ReaderSettings, stored: boolean): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/settings', { record: settings, stored });
	keepingSettings(server, settings);
	return server;
}

describe('the reader settings', () => {
	let settings: Settings;

	beforeEach(() => {
		settings = new Settings();
	});

	it('come from the server, the same in every review', async () => {
		serving({ ...NEW_READER, diff_layout: 'split', theme: 'dark' }, true);

		await settings.load();

		expect(settings.current.diff_layout).toBe('split');
		expect(settings.current.theme).toBe('dark');
	});

	it('take over what this browser kept before the server did, once', async () => {
		localStorage.setItem(LAYOUT_KEPT_HERE, 'split');
		localStorage.setItem(SOUND_KEPT_HERE, 'on');
		const server = serving(NEW_READER, false);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([
			{ ...NOTHING_CHOSEN_HERE, diff_layout: 'split', sound_on_replies: true }
		]);
		expect(settings.current.diff_layout).toBe('split');
		// Dropped, so another review does not hand over stale copies later
		expect(localStorage.getItem(LAYOUT_KEPT_HERE)).toBeNull();
		expect(localStorage.getItem(SOUND_KEPT_HERE)).toBeNull();
	});

	it('take over a theme this browser kept, when the server has nothing stored', async () => {
		localStorage.setItem(THEME_KEPT_HERE, 'dark');
		const server = serving(NEW_READER, false);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ ...NOTHING_CHOSEN_HERE, theme: 'dark' }]);
		expect(settings.current.theme).toBe('dark');
		expect(localStorage.getItem(THEME_KEPT_HERE)).toBe('dark');
	});

	it('keep what this browser kept for next time when the server would not take it', async () => {
		localStorage.setItem(LAYOUT_KEPT_HERE, 'split');
		localStorage.setItem(WHITESPACE_KEPT_HERE, 'on');
		const server = serving(NEW_READER, false);
		server.refuse('PUT /api/settings', SERVER_ERROR);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toHaveLength(1);
		expect(localStorage.getItem(LAYOUT_KEPT_HERE)).toBe('split');
		expect(localStorage.getItem(WHITESPACE_KEPT_HERE)).toBe('on');
	});

	it('stay as a new reader has them, handing nothing over, when the server cannot say', async () => {
		localStorage.setItem(LAYOUT_KEPT_HERE, 'split');
		const server = serving(NEW_READER, false);
		server.refuse('GET /api/settings', SERVER_ERROR);

		await settings.load();

		expect(settings.current).toEqual(NEW_READER);
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([]);
		expect(localStorage.getItem(LAYOUT_KEPT_HERE)).toBe('split');
	});

	it('leave out a choice this browser kept that is no longer a choice', async () => {
		localStorage.setItem(LAYOUT_KEPT_HERE, 'three-columns');
		localStorage.setItem(WHITESPACE_KEPT_HERE, 'on');
		const server = serving(NEW_READER, false);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ ...NOTHING_CHOSEN_HERE, ignore_whitespace: true }]);
	});

	it('hand nothing over when this browser kept nothing', async () => {
		const server = serving(NEW_READER, false);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([]);
	});

	it('take nothing over once the server has settings of its own', async () => {
		localStorage.setItem(LAYOUT_KEPT_HERE, 'split');
		const server = serving(NEW_READER, true);

		await settings.load();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([]);
		expect(settings.current.diff_layout).toBe('unified');
	});

	it('apply a change at once and send only what changed', async () => {
		const server = serving(NEW_READER, true);

		await settings.change({ ignore_whitespace: true });

		expect(settings.current.ignore_whitespace).toBe(true);
		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ ignore_whitespace: true }]);
	});

	it('keep reading with what the tab has when the server cannot be reached', async () => {
		const server = fakeServer();
		server.drop('GET /api/settings');
		server.drop('PUT /api/settings');

		await settings.load();
		await settings.change({ diff_layout: 'split' });

		expect(settings.current.diff_layout).toBe('split');
	});
});
