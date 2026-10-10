/** A server that remembers which release a reader was shown, as `/api/guide` does. */

import type { GuideChange, GuideState } from '$lib/types';
import { fakeServer, type FakeServer, type ReceivedRequest } from './fake-server';

/** Whether what the page sent says which release the reader was shown. */
function isGuideChange(body: unknown): body is GuideChange {
	return typeof body === 'object' && body !== null && 'seen_release' in body && typeof body.seen_release === 'string';
}

/** What `/api/guide` keeps for this reader: the release they were last shown. */
class GuideMemory {
	private seen: string | null;
	private stored: boolean;

	constructor(seen: string | null) {
		this.seen = seen;
		this.stored = seen !== null;
	}

	read(): { record: GuideState; stored: boolean } {
		return { record: { seen_release: this.seen }, stored: this.stored };
	}

	write(request: ReceivedRequest): GuideState {
		if (!isGuideChange(request.body)) throw new Error('The page sent no release for the guide to keep');
		this.seen = request.body.seen_release;
		this.stored = true;
		return { seen_release: this.seen };
	}
}

/** A server remembering which release this reader was shown, as `/api/guide` does. */
export function guideServer(seen: string | null): FakeServer {
	const server = fakeServer();
	const memory = new GuideMemory(seen);
	server.answerWith('GET /api/guide', () => memory.read());
	server.answerWith('PUT /api/guide', (request) => memory.write(request));
	return server;
}
