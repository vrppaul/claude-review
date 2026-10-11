/**
 * Every route the review's page asks of its server, one function each.
 *
 * Each names its route as the server's schema does, sends what that route
 * takes, answers what it answers — the compiler holds all three to the
 * schema — and throws an `ApiError` carrying the server's reason when it refuses.
 * What a failure means for the page is decided by whoever called.
 */

import { read, send, urlOf } from '$lib/api/request';
import type {
	AskRequest,
	CancelRequest,
	DiffResponse,
	FileWindowResponse,
	FollowRequest,
	FollowResponse,
	GuideChange,
	GuideState,
	ImageResponse,
	KeptGuide,
	KeptSettings,
	MessageRequest,
	ReaderSettings,
	RetakeResponse,
	ReviewResponse,
	SettingsChange,
	SubmitRequest,
	SubmitResponse,
	ThreadsResponse,
	VersionsResponse
} from '$lib/types';
import type { Query } from '$lib/types/routes';

/** What the review is and where it stands: read as the page opens. */
export function readReview(): Promise<ReviewResponse> {
	return read('get', '/api/review', { doing: 'Could not open the review' });
}

/** The threads the review holds: what a page that opens with no draft of the review takes in. */
export function readHeldThreads(): Promise<ThreadsResponse> {
	return read('get', '/api/threads', { doing: 'Could not read the threads of the review' });
}

/** Which diff is asked for: whose whitespace, and against which base. */
export interface DiffQuery {
	ignoreWhitespace: boolean;
	/** The key of the base, as the server named it; null for the review's own. */
	base: string | null;
}

/** Take the diff against a base, with whitespace counted or not. */
export function takeDiff(asked: DiffQuery): Promise<DiffResponse> {
	return read('get', '/api/diff', { query: routeQueryOf(asked), doing: 'Could not take the diff' });
}

/** The diff route's query, naming only what the reader changed: whitespace counts unless they said otherwise. */
function routeQueryOf({ ignoreWhitespace, base }: DiffQuery): Query<'get', '/api/diff'> {
	const query: Query<'get', '/api/diff'> = { base };
	if (ignoreWhitespace) query.ignore_whitespace = true;
	return query;
}

/** Take the diff again, after the work a round asked for. */
export function retakeDiff(): Promise<RetakeResponse> {
	return read('post', '/api/retake', { doing: 'Could not take the diff again' });
}

/** What the working tree can be compared against. */
export function offeredVersions(): Promise<VersionsResponse> {
	return read('get', '/api/versions', { doing: 'Could not list what this can be compared against' });
}

/** Lines of a file a hunk left out, from `start` to `end`. */
export function readFileWindow(path: string, start: number, end: number): Promise<FileWindowResponse> {
	return read('get', '/api/file-window', { query: { path, start, end }, doing: `Could not read ${path}` });
}

/** Where each anchor now hangs on the review's diff, in the order asked. */
export function followAnchors(request: FollowRequest): Promise<FollowResponse> {
	return read('post', '/api/anchors/follow', { body: request, doing: 'Could not move the threads' });
}

/** Hand a question asked in a thread over to whoever is answering. */
export function askInThread(request: AskRequest): Promise<void> {
	return send('post', '/api/ask', { body: request, doing: 'Could not ask' });
}

/** Send what has been written: a round, or the end of the review. */
export function submitReview(request: SubmitRequest): Promise<SubmitResponse> {
	return read('post', '/api/submit', { body: request, doing: 'Could not send the review' });
}

/** End a review that was worked through in rounds. */
export function endReview(): Promise<void> {
	return send('post', '/api/end', { doing: 'Could not end the review' });
}

/** Send a message from the agent panel. */
export function sendMessage(request: MessageRequest): Promise<void> {
	return send('post', '/api/message', { body: request, doing: 'Could not send' });
}

/** Take back a message the agent has not answered yet. */
export function cancelMessage(request: CancelRequest): Promise<void> {
	return send('post', '/api/cancel', { body: request, doing: 'Could not stop it' });
}

/** Where the server hands a kept image back. */
export function imageUrl(imageId: string): string {
	return urlOf('/api/images/{image_id}', { pathParameters: { image_id: imageId } });
}

/** Keep an image on the server, the image itself as the body, and say what it is called. */
export function keepImage(image: Blob): Promise<ImageResponse> {
	return read('post', '/api/images', { body: image, doing: 'Could not attach the image' });
}

/** Let the server drop an image taken off before it was sent. */
export function discardImage(imageId: string): Promise<void> {
	return send('delete', '/api/images/{image_id}', {
		pathParameters: { image_id: imageId },
		doing: 'Could not drop the image'
	});
}

/** The reader's settings, and whether any were kept yet. */
export function readSettings(): Promise<KeptSettings> {
	return read('get', '/api/settings', { doing: 'Could not read the settings' });
}

/** Keep these choices for every later review, and say what the settings now are. */
export function keepSettings(changes: SettingsChange): Promise<ReaderSettings> {
	return read('put', '/api/settings', { body: changes, doing: 'Could not keep the settings' });
}

/** How far the reader has been shown around, and whether that was kept yet. */
export function readGuide(): Promise<KeptGuide> {
	return read('get', '/api/guide', { doing: 'Could not read what was shown' });
}

/** Keep how far the reader has been shown around, and say what is now kept. */
export function keepGuide(change: GuideChange): Promise<GuideState> {
	return read('put', '/api/guide', { body: change, doing: 'Could not remember what was shown' });
}
