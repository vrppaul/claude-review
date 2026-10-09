/** A server that remembers which release a reader was shown, as `/api/guide` does. */

import type { GuideState } from '$lib/types';
import { fakeServer, type FakeServer, type ReceivedRequest } from './fake-server';

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
		this.seen = (request.body as GuideState).seen_release;
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
