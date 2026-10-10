/**
 * One way to ask the review's server for anything, held to its schema, and one way it says no.
 *
 * A request names its route as the server's schema does, by method and path,
 * and everything it carries is typed from that route (`types/routes.ts`): the
 * query, the names in the path, the body, and the reply. A path no route has,
 * a method it does not answer, a part it does not take, or a reply read from
 * a route that sends none does not compile. This is the one place the page
 * makes an HTTP request.
 *
 * Every route answers a refusal the same way: a status, and the reason as
 * the `detail` FastAPI uses for its own. The reason is what the reader is
 * shown; the status is the last resort, when the server gave none — a fault
 * on its side answers with plain text, not a reason.
 */

import type { FileRoute, JsonMediaType, JsonRoute, Method, Parts, ReplyOf, SilentRoute } from '$lib/types/routes';

/** A request the server refused, with what the reader is told about it. */
export class ApiError extends Error {
	readonly status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

/** What a request to a route carries: each part the route takes, and what the page was doing. */
type Errand<Verb extends Method, Path extends JsonRoute<Verb> | SilentRoute<Verb>> = Parts<Verb, Path> & {
	/** What was being done, said to the reader when the server gives no reason. */
	doing: string;
};

/**
 * What a request carries, whatever its route, once the compiler has held it
 * to its route: each part is read as it comes.
 */
interface Carried {
	query?: unknown;
	pathParameters?: unknown;
	body?: unknown;
	doing: string;
}

/** Where a request goes, whatever its route: the names in its path, and its query. */
type Address = Pick<Carried, 'query' | 'pathParameters'>;

// A name in a route's path the request fills in: `{image_id}`
const NAMED_IN_PATH = /\{(\w+)\}/g;
const JSON_TYPE: JsonMediaType = 'application/json';

/** Ask a route for what it answers with, and read the JSON it sends. */
export async function read<Verb extends Method, Path extends JsonRoute<Verb>>(
	method: Verb,
	path: Path,
	errand: Errand<Verb, Path>
): Promise<ReplyOf<Verb, Path>> {
	// Trusted to be the shape the server's schema names: both sides are
	// generated from it, and only the kind of a socket push is ever checked
	return (await answerTo(method, path, errand)).json();
}

/** Ask a route to do something it answers with nothing but having done it. */
export async function send<Verb extends Method, Path extends SilentRoute<Verb>>(
	method: Verb,
	path: Path,
	errand: Errand<Verb, Path>
): Promise<void> {
	await answerTo(method, path, errand);
}

/** Where a route is reached with its parts filled in, for a file the browser fetches itself: an image to draw. */
export function urlOf<Path extends FileRoute>(path: Path, parts: Parts<'get', Path>): string {
	return addressOf(path, parts);
}

/** The path with its names filled in, and the query with whatever has a value. */
function addressOf(path: string, { query, pathParameters }: Address): string {
	const names = new Map(entriesOf(pathParameters));
	const filled = path.replace(NAMED_IN_PATH, (_, name: string) => encodeURIComponent(String(names.get(name))));
	const asked = new URLSearchParams();
	for (const [name, value] of entriesOf(query)) {
		// A query leaves out what it does not say; null says nothing too
		if (value !== null && value !== undefined) asked.set(name, String(value));
	}
	const written = asked.toString();
	return written ? `${filled}?${written}` : filled;
}

/** The named values a part holds, none when it is not there. */
function entriesOf(part: unknown): [string, unknown][] {
	return typeof part === 'object' && part !== null ? Object.entries(part) : [];
}

/** Make the request and hand back the server's answer, or throw what the server said if it refused. */
async function answerTo(method: Method, path: string, errand: Carried): Promise<Response> {
	const response = await fetch(addressOf(path, errand), { method: method.toUpperCase(), ...bodyOf(errand.body) });
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
