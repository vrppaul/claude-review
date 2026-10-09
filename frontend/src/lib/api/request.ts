/**
 * One way to ask the review's server for anything, and one way it says no.
 *
 * Every route answers a refusal the same way: a status, and the reason as
 * the `detail` FastAPI uses for its own. The reason is what the reader is
 * shown; the status is the last resort, when the server gave none — a fault
 * on its side answers with plain text, not a reason.
 */

/** A request the server refused, with what the reader is told about it. */
export class ApiError extends Error {
	readonly status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

/** One request to the server, and what it is for. */
export interface Call {
	method: 'GET' | 'PUT' | 'POST' | 'DELETE';
	path: string;
	/**
	 * What goes with it: an image as it is, under its own type, and anything
	 * else as JSON. Nothing for a request that only asks.
	 */
	sent?: Blob | object;
	/** What was being done, said to the reader when the server gives no reason. */
	doing: string;
}

const JSON_TYPE = 'application/json';

/** Make the request, and throw what the server said if it refused. */
export async function call({ method, path, sent, doing }: Call): Promise<Response> {
	const response = await fetch(path, { method, ...bodyOf(sent) });
	if (!response.ok) {
		throw new ApiError(response.status, await reasonOf(response, doing));
	}
	return response;
}

/**
 * Make the request and read the JSON it answers with.
 *
 * Trusted to be the shape the server's schema names: both sides are
 * generated from it, and only the kind of a socket push is ever checked.
 */
export async function read<Reply>(request: Call): Promise<Reply> {
	const response = await call(request);
	return response.json();
}

function bodyOf(sent: Blob | object | undefined): RequestInit {
	if (sent === undefined) return {};
	if (sent instanceof Blob) {
		return { headers: { 'Content-Type': sent.type }, body: sent };
	}
	return { headers: { 'Content-Type': JSON_TYPE }, body: JSON.stringify(sent) };
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
