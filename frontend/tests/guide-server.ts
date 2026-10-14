/** A server that remembers how far a reader was shown around, as `/api/guide` does. */

import type { GuideChange, GuideState } from '$lib/types';
import { fakeServer, type FakeServer, type ReceivedRequest } from './fake-server';

/** What `/api/guide` keeps for this reader: the release they were last shown, and whether Story was introduced. */
class GuideMemory {
	private record: GuideState;
	private stored: boolean;

	constructor(record: GuideState, stored: boolean) {
		this.record = record;
		this.stored = stored;
	}

	read(): { record: GuideState; stored: boolean } {
		return { record: this.record, stored: this.stored };
	}

	/** Each fact the page sent in place of the one kept, as the server applies a change. */
	write(request: ReceivedRequest): GuideState {
		this.record = { ...this.record, ...(request.body as GuideChange) };
		this.stored = true;
		return this.record;
	}
}

/** A server answering `/api/guide` from what it keeps. */
function servingFrom(memory: GuideMemory): FakeServer {
	const server = fakeServer();
	server.answerWith('GET /api/guide', () => memory.read());
	server.answerWith('PUT /api/guide', (request) => memory.write(request));
	return server;
}

/**
 * A server remembering which release this reader was shown, as `/api/guide`
 * does, Story not yet introduced to them; nothing kept for a newcomer.
 */
export function guideServer(seen: string | null): FakeServer {
	return servingFrom(new GuideMemory({ seen_release: seen, story_introduced: false }, seen !== null));
}

/** A server remembering a reader shown this release, Story introduced to them already. */
export function guideServerIntroduced(seen: string): FakeServer {
	return servingFrom(new GuideMemory({ seen_release: seen, story_introduced: true }, true));
}
