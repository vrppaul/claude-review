/**
 * The review's server, as far as a test needs one.
 *
 * Answers what the browser asks by method and path, with replies typed as the
 * server sends them, and keeps every request it received so a test can say
 * what was sent rather than dig through a stub's call list. A route nobody
 * told it about answers 404, as the real server does.
 */
import { vi } from 'vitest';
import type {
	Anchor,
	DiffResponse,
	GuideState,
	ReaderSettings,
	ReviewVersion,
	SubmitResponse
} from '$lib/types';

/** What a route says when it did what it was asked and has nothing to add. */
interface Done {
	status: string;
}

/** What each route answers with when it does what was asked, as the server sends it. */
export interface Replies {
	'GET /api/diff': DiffResponse;
	'GET /api/versions': { versions: ReviewVersion[] };
	'GET /api/file-window': { start: number; lines: string[]; total: number };
	'GET /api/settings': { settings: ReaderSettings; stored: boolean };
	'PUT /api/settings': ReaderSettings;
	'GET /api/guide': { guide: GuideState; stored: boolean };
	'PUT /api/guide': GuideState;
	'POST /api/images': { image_id: string };
	'POST /api/ask': Done;
	'POST /api/message': Done;
	'POST /api/cancel': Done;
	'POST /api/anchors/follow': { anchors: Anchor[] };
	'POST /api/submit': SubmitResponse;
	'POST /api/round': {
		file_count: number;
		round: number;
		changed: string[] | null;
		since: number | null;
	};
	'POST /api/end': Done;
}

export type Route = keyof Replies;

/** A request as the server received it. */
export interface ReceivedRequest {
	method: string;
	path: string;
	query: Record<string, string>;
	/** Parsed when it is JSON; anything else, an uploaded image say, as it was sent. */
	body: unknown;
}

const OK = 200;
const NOT_FOUND = 404;
// What FastAPI says of a route it does not have
const NOT_FOUND_DETAIL = 'Not Found';
/** What a test has a route refuse with. */
export const BAD_REQUEST = 400;
export const UNPROCESSABLE = 422;
export const SERVER_ERROR = 500;
// Only the path and the query matter; relative URLs need something to resolve against
const ORIGIN = 'http://review.test';
const JSON_HEADERS = { 'Content-Type': 'application/json' };
// What the browser throws when the request never reached a server
const UNREACHABLE = 'Failed to fetch';

/** Takes a request that waits to be answered, and the way to answer it. */
interface Holder {
	take(request: ReceivedRequest, respond: (response: Response) => void): void;
}

/** How a route answers whatever arrives on it. */
type Answer =
	| { kind: 'reply'; reply: (request: ReceivedRequest) => unknown }
	| { kind: 'refuse'; status: number; detail: string }
	| { kind: 'drop' }
	| { kind: 'hold'; holder: Holder };

/** One request held on a route, with the way to answer it. */
interface Waiting {
	request: ReceivedRequest;
	respond: (response: Response) => void;
}

/** Requests to one route that wait until the test answers them, in any order. */
export class HeldReplies<R extends Route> implements Holder {
	private readonly waiting: Waiting[] = [];

	take(request: ReceivedRequest, respond: (response: Response) => void): void {
		this.waiting.push({ request, respond });
	}

	/** What has arrived and is waiting, in the order it arrived. */
	get requests(): ReceivedRequest[] {
		return this.waiting.map((held) => held.request);
	}

	/** Answer the request that arrived `position`-th, counting from zero. */
	answer(position: number, reply: Replies[R]): void {
		const held = this.waiting[position];
		if (!held) {
			throw new Error(`Only ${this.waiting.length} requests are waiting, not ${position + 1}`);
		}
		held.respond(jsonResponse(OK, reply));
	}
}

export class FakeServer {
	/** Everything received, in the order it arrived. */
	readonly requests: ReceivedRequest[] = [];
	private readonly answers = new Map<string, Answer>();

	/** Answer every request to the route with this reply. */
	answer<R extends Route>(route: R, reply: Replies[R]): void {
		this.answers.set(route, { kind: 'reply', reply: () => reply });
	}

	/** Answer every request to the route with what the request itself decides. */
	answerWith<R extends Route>(route: R, reply: (request: ReceivedRequest) => Replies[R]): void {
		this.answers.set(route, { kind: 'reply', reply });
	}

	/** Refuse every request to the route, saying why the way FastAPI does. */
	refuse(route: Route, status: number, detail = `Refused with ${status}`): void {
		this.answers.set(route, { kind: 'refuse', status, detail });
	}

	/** Let every request to the route fail to arrive, as when the server is gone. */
	drop(route: Route): void {
		this.answers.set(route, { kind: 'drop' });
	}

	/** Hold every request to the route until the test answers it. */
	hold<R extends Route>(route: R): HeldReplies<R> {
		const held = new HeldReplies<R>();
		this.answers.set(route, { kind: 'hold', holder: held });
		return held;
	}

	/** What arrived on one route, in order. */
	requestsTo(route: Route): ReceivedRequest[] {
		return this.requests.filter((request) => routeOf(request) === route);
	}

	/** The bodies sent to one route, in order. */
	bodiesSentTo(route: Route): unknown[] {
		return this.requestsTo(route).map((request) => request.body);
	}

	/** What `fetch` does while this server is up. */
	receive(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
		const request = received(input, init);
		this.requests.push(request);
		const answer = this.answers.get(routeOf(request));
		if (!answer) return Promise.resolve(jsonResponse(NOT_FOUND, { detail: NOT_FOUND_DETAIL }));

		switch (answer.kind) {
			case 'reply':
				return Promise.resolve(jsonResponse(OK, answer.reply(request)));
			case 'refuse':
				return Promise.resolve(jsonResponse(answer.status, { detail: answer.detail }));
			case 'drop':
				return Promise.reject(new TypeError(UNREACHABLE));
			case 'hold':
				return new Promise((respond) => answer.holder.take(request, respond));
		}
	}
}

/** Put a server in place of the network for the rest of the test. */
export function fakeServer(): FakeServer {
	const server = new FakeServer();
	vi.stubGlobal('fetch', (input: RequestInfo | URL, init?: RequestInit) =>
		server.receive(input, init)
	);
	return server;
}

/** What a reader who has never chosen anything has. */
export const NEW_READER: ReaderSettings = {
	theme: 'system',
	diff_layout: 'unified',
	ignore_whitespace: false,
	sound_on_replies: false
};

/** Have the server take every settings change on top of these, and answer with the result. */
export function keepingSettings(server: FakeServer, settings: ReaderSettings = NEW_READER): void {
	server.answerWith('PUT /api/settings', (request) => ({
		...settings,
		...(request.body as Partial<ReaderSettings>)
	}));
}

/** A server taking every message sent from the agent panel, and every one taken back. */
export function listeningToThePanel(server: FakeServer = fakeServer()): FakeServer {
	server.answer('POST /api/message', { status: 'sent' });
	server.answer('POST /api/cancel', { status: 'cancelled' });
	return server;
}

function routeOf(request: ReceivedRequest): string {
	return `${request.method} ${request.path}`;
}

function received(input: RequestInfo | URL, init: RequestInit): ReceivedRequest {
	const url = new URL(input instanceof Request ? input.url : String(input), ORIGIN);
	return {
		method: (init.method ?? 'GET').toUpperCase(),
		path: url.pathname,
		query: Object.fromEntries(url.searchParams),
		body: parsedBody(init.body)
	};
}

function parsedBody(body: RequestInit['body']): unknown {
	if (typeof body !== 'string') return body ?? null;
	try {
		return JSON.parse(body);
	} catch {
		return body;
	}
}

function jsonResponse(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}
