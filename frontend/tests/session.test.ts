import { describe, it, expect, beforeEach, vi } from 'vitest';
import { dispatchHeld, openSession, type ServerMessage } from '$lib/stores/session.svelte';

/** A socket that opens at once and lets the test say what the server sends. */
class FakeSocket {
	static readonly OPEN = 1;
	static opened: FakeSocket[] = [];
	readyState = FakeSocket.OPEN;
	sent: string[] = [];
	private readonly listeners = new Map<string, ((event: { data?: string }) => void)[]>();

	constructor(readonly url: string) {
		FakeSocket.opened.push(this);
	}

	addEventListener(kind: string, listener: (event: { data?: string }) => void) {
		this.listeners.set(kind, [...(this.listeners.get(kind) ?? []), listener]);
	}

	send(text: string) {
		this.sent.push(text);
	}

	close() {}

	emit(kind: string, data?: string) {
		for (const listener of this.listeners.get(kind) ?? []) listener({ data });
	}
}

describe('the session socket', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
	});

	it('holds what arrives before the review has restored its draft, then hands it over in order', () => {
		const heard: ServerMessage[] = [];
		const close = openSession((message) => heard.push(message));
		const [socket] = FakeSocket.opened;

		socket.emit('message', JSON.stringify({ type: 'reply', text: 'first' }));
		socket.emit('message', JSON.stringify({ type: 'chat', text: 'second' }));
		expect(heard).toEqual([]);

		dispatchHeld();
		socket.emit('message', JSON.stringify({ type: 'show', file: 'a.py' }));

		expect(heard.map((message) => message.type)).toEqual(['reply', 'chat', 'show']);
		close();
	});

	it('passes over what it cannot read and keeps listening', () => {
		const heard: ServerMessage[] = [];
		const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
		const close = openSession((message) => heard.push(message));
		dispatchHeld();
		const [socket] = FakeSocket.opened;

		socket.emit('message', 'not json');
		socket.emit('message', JSON.stringify({ text: 'no type' }));
		socket.emit('message', JSON.stringify({ type: 'reply', text: 'fine' }));

		expect(heard.map((message) => message.type)).toEqual(['reply']);
		expect(warn).toHaveBeenCalledTimes(2);
		close();
	});

	it('does not hide a fault in whatever handles a message', () => {
		const close = openSession(() => {
			throw new Error('handler broke');
		});
		dispatchHeld();
		const [socket] = FakeSocket.opened;

		expect(() => socket.emit('message', JSON.stringify({ type: 'reply' }))).toThrow(
			'handler broke'
		);
		close();
	});
});
