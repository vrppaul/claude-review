/**
 * The review's server, as far as a test needs one.
 *
 * Answers what the browser asks by method and path, with replies typed as the
 * server sends them, and keeps every request it received so a test can say
 * what was sent rather than dig through a stub's call list. A route nobody
 * told it about answers 404, as the real server does.
 */
import { vi } from 'vitest';
import type { paths } from '$lib/types/generated/http';
import type { ReaderSettings, SettingsChange } from '$lib/types';

/** What a route answers when it did what it was asked and has nothing to add: no body at all. */
type Done = null;

/** How the server's schema names the methods a route answers. */
type Method = 'get' | 'put' | 'post' | 'delete';

/**
 * What a route answers when it does what was asked, read from the server's
 * own schema: the JSON it sends, or nothing for a route that sends no body.
 * A route the server does not have, or a method it does not answer, does
 * not compile.
 */
type ReplyOf<Path extends keyof paths, Verb extends Method> = paths[Path][Verb] extends {
	responses: infer Responses;
}
	? Responses extends { 200: { content: { 'application/json': infer Body } } }
		? Body
		: Responses extends { 204: unknown }
			? Done
			: never
	: never;

/** What each route the page uses answers with when it does what was asked. */
export interface Replies {
	'GET /api/review': ReplyOf<'/api/review', 'get'>;
	'GET /api/diff': ReplyOf<'/api/diff', 'get'>;
	'GET /api/versions': ReplyOf<'/api/versions', 'get'>;
	'GET /api/file-window': ReplyOf<'/api/file-window', 'get'>;
	'GET /api/settings': ReplyOf<'/api/settings', 'get'>;
	'PUT /api/settings': ReplyOf<'/api/settings', 'put'>;
	'GET /api/guide': ReplyOf<'/api/guide', 'get'>;
	'PUT /api/guide': ReplyOf<'/api/guide', 'put'>;
	'POST /api/images': ReplyOf<'/api/images', 'post'>;
	'POST /api/ask': ReplyOf<'/api/ask', 'post'>;
	'POST /api/message': ReplyOf<'/api/message', 'post'>;
	'POST /api/cancel': ReplyOf<'/api/cancel', 'post'>;
	'POST /api/anchors/follow': ReplyOf<'/api/anchors/follow', 'post'>;
	'POST /api/submit': ReplyOf<'/api/submit', 'post'>;
	'POST /api/retake': ReplyOf<'/api/retake', 'post'>;
	'POST /api/end': ReplyOf<'/api/end', 'post'>;
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

const SUCCEEDED = 200;
// What a route answers when it did what was asked and has nothing to add
const NO_CONTENT = 204;
const NOT_FOUND = 404;
// What FastAPI says of a route it does not have
const NOT_FOUND_DETAIL = 'Not Found';
// What FastAPI says of a request whose body its schema refuses: a list of
// what is wrong where, not a sentence
const INVALID_REQUEST_DETAIL = [{ loc: ['body'], msg: 'Field required', type: 'missing' }];
// What a fault on the server's side answers with: plain text, no reason
const FAULT_TEXT = 'Internal Server Error';
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
	| { kind: 'refuse'; status: number; detail: unknown }
	| { kind: 'fail'; status: number }
	| { kind: 'drop' }
	| { kind: 'hold'; holder: Holder };

/** One request held on a route, with the way to answer it. */
interface Waiting {
	request: ReceivedRequest;
	respond: (response: Response) => void;
}

/** Requests to one route that wait until the test answers them, in any order. */
export class HeldReplies<Held extends Route> implements Holder {
	private readonly waiting: Waiting[] = [];

	take(request: ReceivedRequest, respond: (response: Response) => void): void {
		this.waiting.push({ request, respond });
	}

	/** What has arrived and is waiting, in the order it arrived. */
	get requests(): ReceivedRequest[] {
		return this.waiting.map((held) => held.request);
	}

	/** Answer the request that arrived `position`-th, counting from zero. */
	answer(position: number, reply: Replies[Held]): void {
		const held = this.waiting[position];
		if (!held) {
			throw new Error(`Only ${this.waiting.length} requests are waiting, not ${position + 1}`);
		}
		held.respond(replyResponse(reply));
	}
}

export class FakeServer {
	/** Everything received, in the order it arrived. */
	readonly requests: ReceivedRequest[] = [];
	private readonly answers = new Map<string, Answer>();

	/** Answer every request to the route with this reply. */
	answer<Answered extends Route>(route: Answered, reply: Replies[Answered]): void {
		this.answers.set(route, { kind: 'reply', reply: () => reply });
	}

	/** Answer every request to the route with what the request itself decides. */
	answerWith<Answered extends Route>(route: Answered, reply: (request: ReceivedRequest) => Replies[Answered]): void {
		this.answers.set(route, { kind: 'reply', reply });
	}

	/** Refuse every request to the route, saying why the way FastAPI does. */
	refuse(route: Route, status: number, detail = `Refused with ${status}`): void {
		this.answers.set(route, { kind: 'refuse', status, detail });
	}

	/** Refuse every request to the route as FastAPI refuses a body its schema does not take. */
	refuseAsInvalid(route: Route): void {
		this.answers.set(route, { kind: 'refuse', status: UNPROCESSABLE, detail: INVALID_REQUEST_DETAIL });
	}

	/** Answer every request to the route with a fault of the server's own, which gives no reason. */
	fail(route: Route, status: number): void {
		this.answers.set(route, { kind: 'fail', status });
	}

	/** Let every request to the route fail to arrive, as when the server is gone. */
	drop(route: Route): void {
		this.answers.set(route, { kind: 'drop' });
	}

	/** Hold every request to the route until the test answers it. */
	hold<Held extends Route>(route: Held): HeldReplies<Held> {
		const held = new HeldReplies<Held>();
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
				return Promise.resolve(replyResponse(answer.reply(request)));
			case 'refuse':
				return Promise.resolve(jsonResponse(answer.status, { detail: answer.detail }));
			case 'fail':
				return Promise.resolve(new Response(FAULT_TEXT, { status: answer.status }));
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
	vi.stubGlobal('fetch', (input: RequestInfo | URL, init?: RequestInit) => server.receive(input, init));
	return server;
}

/** What a reader who has never chosen anything has. */
export const NEW_READER: ReaderSettings = {
	theme: 'system',
	diff_layout: 'unified',
	ignore_whitespace: false,
	sound_on_replies: false
};

// Every choice a change of the reader's settings may carry
const SETTINGS_FIELDS: readonly string[] = [
	'theme',
	'diff_layout',
	'ignore_whitespace',
	'sound_on_replies'
] satisfies (keyof SettingsChange)[];

/** Whether what the page sent is a change of the reader's choices, and nothing else. */
function isSettingsChange(body: unknown): body is SettingsChange {
	return (
		typeof body === 'object' && body !== null && Object.keys(body).every((field) => SETTINGS_FIELDS.includes(field))
	);
}

/** The settings once a change is taken on top of them: a choice sent as null is one not sent, as the server reads it. */
function changedBy(settings: ReaderSettings, change: SettingsChange): ReaderSettings {
	return {
		theme: change.theme ?? settings.theme,
		diff_layout: change.diff_layout ?? settings.diff_layout,
		ignore_whitespace: change.ignore_whitespace ?? settings.ignore_whitespace,
		sound_on_replies: change.sound_on_replies ?? settings.sound_on_replies
	};
}

/** Have the server take every settings change on top of these, and answer with the result. */
export function keepingSettings(server: FakeServer, settings: ReaderSettings = NEW_READER): void {
	server.answerWith('PUT /api/settings', (request) => {
		if (!isSettingsChange(request.body)) throw new Error('The page sent something other than a settings change');
		return changedBy(settings, request.body);
	});
}

/** A server taking every message sent from the agent panel, and every one taken back. */
export function listeningToThePanel(server: FakeServer = fakeServer()): FakeServer {
	server.answer('POST /api/message', null);
	server.answer('POST /api/cancel', null);
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

/** A route doing what it was asked: what it says, or nothing at all when it has nothing to add. */
function replyResponse(reply: unknown): Response {
	return reply === null ? new Response(null, { status: NO_CONTENT }) : jsonResponse(SUCCEEDED, reply);
}

function jsonResponse(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}
