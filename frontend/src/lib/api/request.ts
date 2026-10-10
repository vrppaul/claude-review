/**
 * One way to ask the review's server for anything, held to its schema, and one way it says no.
 *
 * A request names its route as the server's schema does, by method and path,
 * and everything it carries is typed from that route: the query, the
 * parameters in the path, the body, and the reply. A path no route has, a
 * method it does not answer, a part it does not take, or a reply read from a
 * route that sends none does not compile.
 *
 * Every route answers a refusal the same way: a status, and the reason as
 * the `detail` FastAPI uses for its own. The reason is what the reader is
 * shown; the status is the last resort, when the server gave none — a fault
 * on its side answers with plain text, not a reason.
 */

import type { paths } from '$lib/types/generated/http';

/** A request the server refused, with what the reader is told about it. */
export class ApiError extends Error {
	readonly status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

/** How the server's schema names the methods the page asks with. */
type Method = 'get' | 'put' | 'post' | 'delete';

// The statuses a route answers with when it does what was asked: with a body, and with none
const DONE = 200;
const DONE_WITH_NOTHING_TO_SAY = 204;

/** What a route answers when it does what was asked and sends JSON. */
interface JsonReply<Body> {
	[DONE]: { content: { 'application/json': Body } };
}
/** What a route answers when it does what was asked and sends nothing. */
interface NoReply {
	[DONE_WITH_NOTHING_TO_SAY]: unknown;
}

/** The path of every route that answers a method, with a reply of a kind. */
type RouteAnswering<Verb extends Method, Reply> = {
	[Path in keyof paths]: paths[Path][Verb] extends { responses: Reply } ? Path : never;
}[keyof paths];

/** What the server's schema says of one method of one route. */
type Operation<Verb extends Method, Path extends keyof paths> = paths[Path][Verb];

/** The JSON a route answers with when it does what was asked. */
type ReplyOf<Asked> = Asked extends { responses: JsonReply<infer Body> } ? Body : never;

/** What a route takes in its query, as its schema names it. */
type QueryOf<Asked> = Asked extends { parameters: { query?: infer Query } } ? Query : never;

/** What a route takes in its path: the names its path has a place for. */
type NamedInPathOf<Asked> = Asked extends { parameters: { path?: infer Named } } ? Named : never;

/** What a route takes as its body: JSON of its model, or a file as it is, an image say. */
type BodyOf<Asked> = Asked extends { requestBody: { content: { 'application/json': infer Json } } }
	? Json
	: Asked extends { requestBody: { content: object } }
		? Blob
		: never;

/** A part of a request: given when the route takes it, never when it does not. */
type Part<Name extends string, Taken> = [Taken] extends [never] ? { [Key in Name]?: never } : { [Key in Name]: Taken };

/** What a request to a route carries: each part the route takes, and what the page was doing. */
type Errand<Asked> = Part<'query', QueryOf<Asked>> &
	Part<'pathParameters', NamedInPathOf<Asked>> &
	Part<'body', BodyOf<Asked>> & {
		/** What was being done, said to the reader when the server gives no reason. */
		doing: string;
	};

/** The query one route takes, for a caller that builds it up a part at a time. */
export type Query<Verb extends Method, Path extends keyof paths> = QueryOf<Operation<Verb, Path>>;

/**
 * What a request carries, whatever its route: how it is sent once the
 * compiler has held it to its route. Each part is read as it comes.
 */
interface Sent {
	query?: unknown;
	pathParameters?: unknown;
	body?: unknown;
	doing: string;
}

/** Where a request goes, whatever its route: its path's names, and its query. */
type Located = Pick<Sent, 'query' | 'pathParameters'>;

// A name in a route's path the request fills in: `{image_id}`
const NAMED_IN_PATH = /\{(\w+)\}/g;
const JSON_TYPE = 'application/json';

/** Ask a route for what it answers with, and read the JSON it sends. */
export async function read<Verb extends Method, Path extends RouteAnswering<Verb, JsonReply<unknown>>>(
	method: Verb,
	path: Path,
	errand: Errand<Operation<Verb, Path>>
): Promise<ReplyOf<Operation<Verb, Path>>> {
	// Trusted to be the shape the server's schema names: both sides are
	// generated from it, and only the kind of a socket push is ever checked
	return (await sent(method, path, errand)).json();
}

/** Ask a route to do something it answers with nothing but having done it. */
export async function send<Verb extends Method, Path extends RouteAnswering<Verb, NoReply>>(
	method: Verb,
	path: Path,
	errand: Errand<Operation<Verb, Path>>
): Promise<void> {
	await sent(method, path, errand);
}

/** Where a route is reached with its parts filled in: an image to draw, say, which the browser fetches itself. */
export function urlOf<Path extends RouteAnswering<'get', object>>(
	path: Path,
	errand: Omit<Errand<Operation<'get', Path>>, 'doing'>
): string {
	return located(path, errand);
}

/** The path with its names filled in, and the query with whatever has a value. */
function located(path: string, { query, pathParameters }: Located): string {
	const names = new Map(Object.entries(pathParameters ?? {}));
	const filled = path.replace(NAMED_IN_PATH, (_, name: string) => encodeURIComponent(String(names.get(name))));
	const asked = new URLSearchParams();
	for (const [name, value] of Object.entries(query ?? {})) {
		// A query leaves out what it does not say; null says nothing too
		if (value !== null && value !== undefined) asked.set(name, String(value));
	}
	const written = asked.toString();
	return written ? `${filled}?${written}` : filled;
}

/** Make the request, and throw what the server said if it refused. */
async function sent(method: Method, path: string, errand: Sent): Promise<Response> {
	const response = await fetch(located(path, errand), { method: method.toUpperCase(), ...bodyOf(errand.body) });
	if (!response.ok) {
		throw new ApiError(response.status, await reasonOf(response, errand.doing));
	}
	return response;
}

/** A body as it goes: a file as it is, under its own type, and anything else as JSON. */
function bodyOf(body: unknown): RequestInit {
	if (body === undefined) return {};
	if (body instanceof Blob) {
		return { headers: { 'Content-Type': body.type }, body };
	}
	return { headers: { 'Content-Type': JSON_TYPE }, body: JSON.stringify(body) };
}

/** Why the server refused, in words the reader can act on. */
async function reasonOf(response: Response, doing: string): Promise<string> {
	try {
		const said: { detail?: unknown } = await response.json();
		if (typeof said.detail === 'string') return said.detail;
	} catch {
		// Not JSON: the status is all there is
	}
	return `${doing}: ${response.status}`;
}
