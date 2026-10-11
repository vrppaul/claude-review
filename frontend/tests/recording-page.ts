/** A page on the session socket, for the connection's tests: what it is handed, and where its telling stands. */
import { vi } from 'vitest';
import { FIRST_RETRY, PageConnection, type PushReceiver } from '$lib/connection/page-connection';
import type { ServerPush, TellingPosition } from '$lib/types';
import { latestSocket, REVIEW_IDENTITY, THIS_RUN } from './fake-socket';

// Pushes as the server sends them
export const A_REPLY: ServerPush = { type: 'reply', thread_id: 'comment-1', question_id: null, body: 'first' };
export const A_CHAT: ServerPush = { type: 'chat', message_id: null, body: 'second', files: [] };

// Where the page's socket is; the fake socket only keeps it
export const SESSION_URL = 'ws://review.test/api/session';

// How far the review's telling had got when the page connected
export const TOLD_BEFORE = 3;

/**
 * A page that notes what it is handed, and catches up when asked, finishing
 * when the test says. Its telling starts where its facts left it, and moves
 * with every push it takes in, as a review's does.
 */
export class RecordingPage implements PushReceiver {
	readonly identity = REVIEW_IDENTITY;
	readonly heard: ServerPush[] = [];
	readonly heardAt: TellingPosition[] = [];
	readonly caughtUpFrom: TellingPosition[] = [];
	position: TellingPosition = { instance: THIS_RUN, sequence: TOLD_BEFORE };
	/** Whether another review answered on the port, and the connection let go. */
	strayedOff = false;
	#finish: (() => void) | null = null;

	get catchUps(): number {
		return this.caughtUpFrom.length;
	}

	told(): TellingPosition {
		return this.position;
	}

	take(push: ServerPush, at: TellingPosition): void {
		this.heard.push(push);
		this.heardAt.push(at);
		this.position = at;
	}

	catchUp(from: TellingPosition): Promise<void> {
		this.caughtUpFrom.push(from);
		this.position = from;
		return new Promise((resolve) => (this.#finish = resolve));
	}

	strayed(): void {
		this.strayedOff = true;
	}

	/** The page has caught up; what the connection held is handed over once it hears so. */
	finishCatchingUp(): void {
		this.#finish?.();
	}
}

/** A page that breaks taking in one kind of push, and takes in every other. */
export class PageThatBreaksOn extends RecordingPage {
	readonly #breaksOn: ServerPush['type'];

	constructor(breaksOn: ServerPush['type']) {
		super();
		this.#breaksOn = breaksOn;
	}

	override take(push: ServerPush, at: TellingPosition): void {
		if (push.type === this.#breaksOn) throw new Error(`the page broke taking in a ${push.type}`);
		super.take(push, at);
	}
}

/** A connection opened before any page can take what it brings: it holds the review on screen. */
export function opened(): PageConnection {
	const connection = new PageConnection(SESSION_URL);
	connection.open();
	return connection;
}

/** A connection opened, and then handed to a page, going on from where the page's telling stands. */
export function connected(page = new RecordingPage()): PageConnection {
	const connection = opened();
	connection.deliverTo(page);
	return connection;
}

/** Drop the socket and let the connection come back on a socket of its own. */
export function dropAndComeBack(): void {
	latestSocket().drop();
	vi.advanceTimersByTime(FIRST_RETRY);
	latestSocket().accept();
}
