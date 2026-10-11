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
 * the `detail` FastAPI uses for its own — in words, or field by field, each
 * named by its place in what was sent. The reason is what the reader is
 * shown; the status is the last resort, when the server gave none — a fault
 * on its side answers with plain text, not a reason. A request that never
 * reached the review — its server gone, or not yet back — is said in words
 * too, rather than in the browser's own. Whatever went wrong, the reader is
 * told it here, once, in what the page was doing.
 */

import type { FieldRefusal, Refusal } from '$lib/types';
import type {
	FileRoute,
	JsonMediaType,
	JsonRoute,
	Method,
	Parts,
	PathNames,
	QueryWords,
	ReplyOf,
	SilentRoute
} from '$lib/types/routes';

/** A request the server refused, or one that never reached it, with what the reader is told about it. */
export class ApiError extends Error {
	/** What the server refused with; null when nothing answered at all. */
	readonly status: number | null;

	constructor(status: number | null, message: string) {
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
 * to its route: a query and the names in a path as every route's schema has
 * them, and a body, read as it comes.
 */
interface Carried {
	query?: QueryWords;
	pathParameters?: PathNames;
	body?: unknown;
	doing: string;
}

/** Where a request goes, whatever its route: the names in its path, and its query. */
type Address = Pick<Carried, 'query' | 'pathParameters'>;

// A name in a route's path the request fills in: `{image_id}`
const NAMED_IN_PATH = /\{(\w+)\}/g;
const JSON_TYPE: JsonMediaType = 'application/json';
// What the reader is told of a request nothing answered
const UNANSWERED = 'the review did not answer';
// How a refused field's place is written, and what stands between two refused fields
const PLACE_SEPARATOR = '.';
const FIELDS_SEPARATOR = '; ';
// The parts of a request the server names a field's place from, which say
// nothing to the reader: where in what was sent is the field itself
const REQUEST_PARTS = new Set<FieldRefusal['loc'][number]>(['body', 'query', 'path']);

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
		// A query leaves out what it does not say: null says nothing
		if (value !== null) asked.set(name, String(value));
	}
	const written = asked.toString();
	return written ? `${filled}?${written}` : filled;
}

/** The named values a part holds, none when it is not there. */
function entriesOf<Value>(part: Readonly<Record<string, Value>> | undefined): [string, Value][] {
	return part ? Object.entries(part) : [];
}

/** Make the request and hand back the server's answer, or throw what went wrong, in words. */
async function answerTo(method: Method, path: string, errand: Carried): Promise<Response> {
	const response = await reached(addressOf(path, errand), { method: method.toUpperCase(), ...bodyOf(errand.body) });
	if (response === null) throw new ApiError(null, `${errand.doing}: ${UNANSWERED}`);
	if (!response.ok) {
		throw new ApiError(response.status, await reasonOf(response, errand.doing));
	}
	return response;
}

/** The server's answer, or null when the request never reached it: the browser only rejects a fetch nothing answered. */
async function reached(address: string, init: RequestInit): Promise<Response | null> {
	try {
		return await fetch(address, init);
	} catch {
		return null;
	}
}

/** A body as it goes: a file as it is, under its own type, and anything else as JSON. */
function bodyOf(body: unknown): RequestInit {
	if (body === undefined) return {};
	if (body instanceof Blob) {
		return { headers: { 'Content-Type': body.type }, body };
	}
	return { headers: { 'Content-Type': JSON_TYPE }, body: JSON.stringify(body) };
}

/** Why the server refused, in words the reader can act on: its own, or each field it found wrong and why. */
async function reasonOf(response: Response, doing: string): Promise<string> {
	const refusal = await refusalIn(response);
	if (refusal === null) return `${doing}: ${response.status}`;
	if (typeof refusal.detail === 'string') return refusal.detail;
	return `${doing}: ${refusal.detail.map(fieldSaidWrong).join(FIELDS_SEPARATOR)}`;
}

/** The refusal an answer carries, or null for one that carries none: a fault on the server's side says plain text. */
async function refusalIn(response: Response): Promise<Refusal | null> {
	try {
		return await response.json();
	} catch {
		return null;
	}
}

/** One field the server found wrong, named by its place in what was sent, and why. */
function fieldSaidWrong({ loc, msg }: FieldRefusal): string {
	const [part, ...inPart] = loc;
	const place = part !== undefined && REQUEST_PARTS.has(part) ? inPart : loc;
	return place.length > 0 ? `${place.join(PLACE_SEPARATOR)}: ${msg}` : msg;
}
