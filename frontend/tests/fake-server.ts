/**
 * The review's server, as far as a test needs one.
 *
 * Answers what the browser asks by method and path, with replies typed as the
 * server sends them, and keeps every request it received so a test can say
 * what was sent rather than dig through a stub's call list. A request no route
 * of the page's takes is refused as the real server refuses one: 405 where a
 * route is at its path under another method, naming the methods taken there,
 * and 404 elsewhere — of the server's routes, it knows those the page uses. A
 * route the page uses that the test did not say how to answer fails the test
 * once it is over: the real server would have answered it, and a test must
 * not run a failure path unknowingly.
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
 * A route the server does not have, or a method it does not answer, has no
 * reply to give: an editor says so at once, though no gate type-checks the
 * tests.
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

/**
 * Every route the page asks the server through `fetch`, by its method and
 * its path as the schema writes it, path parameters and all. An image the
 * browser fetches itself, by the address the page writes for it, is not one.
 */
const ROUTES = [
	'GET /api/review',
	'GET /api/threads',
	'GET /api/diff',
	'GET /api/versions',
	'GET /api/file-window',
	'GET /api/settings',
	'PUT /api/settings',
	'GET /api/guide',
	'PUT /api/guide',
	'POST /api/images',
	'DELETE /api/images/{image_id}',
	'POST /api/ask',
	'POST /api/message',
	'POST /api/cancel',
	'POST /api/anchors/follow',
	'POST /api/submit',
	'POST /api/retake',
	'POST /api/end'
] as const;

export type Route = (typeof ROUTES)[number];

/** What one route answers with when it does what was asked, read from its method and path. */
type ReplyOfRoute<Asked extends Route> = Asked extends `${infer Verb} ${infer Path}`
	? Path extends keyof paths
		? ReplyOf<Path, Lowercase<Verb> & Method>
		: never
	: never;

/** What each route the page uses answers with when it does what was asked. */
export type Replies = { [Asked in Route]: ReplyOfRoute<Asked> };

/** A route the page uses, told apart by its method and by a pattern its path is matched with. */
interface RoutePattern {
	route: Route;
	method: string;
	path: RegExp;
}

// What a path parameter stands for in a path as the schema writes it: one
// part of the path, whatever it says
const PATH_PARAMETER = /\{[^}]+\}/g;
const ONE_PATH_PART = '[^/]+';

/** How a request's method and path are matched to a route. */
function patternOf(route: Route): RoutePattern {
	const [method, path] = route.split(' ');
	return { route, method, path: new RegExp(`^${path.replace(PATH_PARAMETER, ONE_PATH_PART)}$`) };
}

const ROUTE_PATTERNS = ROUTES.map(patternOf);

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
// What FastAPI says of a path it has no route at
const NOT_FOUND_DETAIL = 'Not Found';
// What it answers a method the route at a path does not take, naming those it does
const METHOD_NOT_ALLOWED = 405;
const METHOD_NOT_ALLOWED_DETAIL = 'Method Not Allowed';
const ALLOW_SEPARATOR = ', ';
// What the server says of a request whose body its schema refuses: a list of
// what is wrong where, not a sentence
const INVALID_REQUEST_DETAIL = [
	{ loc: ['body', 'threads', 1, 'body'], msg: 'String should have at most 50000 characters' },
	{ loc: ['body', 'end'], msg: 'Field required' }
];
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
	/** What arrived on a route the page uses that the test did not say how to answer. */
	readonly unanswered: ReceivedRequest[] = [];
	private readonly answers = new Map<Route, Answer>();

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
		return this.requests.filter((request) => routeOf(request)?.route === route);
	}

	/** The bodies sent to one route, in order. */
	bodiesSentTo(route: Route): unknown[] {
		return this.requestsTo(route).map((request) => request.body);
	}

	/** What `fetch` does while this server is up. */
	receive(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
		const request = received(input, init);
		this.requests.push(request);
		const route = routeOf(request);
		if (route === null) return Promise.resolve(refusedAsTheServerRefuses(request));
		const answer = this.answers.get(route.route);
		if (!answer) {
			this.unanswered.push(request);
			return Promise.reject(new Error(`The test did not say how ${route.route} answers`));
		}

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

// The servers put in place of the network during the test running now
const serversThisTest: FakeServer[] = [];

/** Put a server in place of the network for the rest of the test. */
export function fakeServer(): FakeServer {
	const server = new FakeServer();
	serversThisTest.push(server);
	vi.stubGlobal('fetch', (input: RequestInfo | URL, init?: RequestInit) => server.receive(input, init));
	return server;
}

/**
 * Fail the test that has just run if the page asked a route of its server
 * the test did not say how to answer; then forget its servers.
 */
export function failOnUnanswered(): void {
	const unanswered = serversThisTest.splice(0).flatMap((server) => server.unanswered);
	if (unanswered.length > 0) {
		const asked = unanswered.map((request) => `${request.method} ${request.path}`).join(', ');
		throw new Error(`The page asked what the test did not say how to answer: ${asked}`);
	}
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

/** The route of the page's a request was sent to; null when none takes its method at its path. */
function routeOf(request: ReceivedRequest): RoutePattern | null {
	return ROUTE_PATTERNS.find(({ method, path }) => method === request.method && path.test(request.path)) ?? null;
}

/** What the real server answers a request no route takes: 405 naming the methods taken at its path, or 404. */
function refusedAsTheServerRefuses(request: ReceivedRequest): Response {
	const taken = ROUTE_PATTERNS.filter(({ path }) => path.test(request.path)).map(({ method }) => method);
	if (taken.length === 0) return jsonResponse(NOT_FOUND, { detail: NOT_FOUND_DETAIL });
	return new Response(JSON.stringify({ detail: METHOD_NOT_ALLOWED_DETAIL }), {
		status: METHOD_NOT_ALLOWED,
		headers: { ...JSON_HEADERS, Allow: taken.join(ALLOW_SEPARATOR) }
	});
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
