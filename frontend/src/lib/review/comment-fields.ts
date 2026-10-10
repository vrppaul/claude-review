/**
 * What happens to the comment fields on the page, for whoever follows along.
 *
 * What holds the fields says when one opens and how it goes — added, asked,
 * or put away unsent — and knows nothing of who is listening. The tour
 * listens; nothing a field does depends on it.
 */

import type { CommentFieldEvent } from '$lib/types';

type Listener = (event: CommentFieldEvent) => void;

export class CommentFields {
	readonly #listeners = new Set<Listener>();

	report(event: CommentFieldEvent): void {
		for (const listener of this.#listeners) listener(event);
	}

	/** Follow every field from now on; returns how to stop. */
	listen(listener: Listener): () => void {
		this.#listeners.add(listener);
		return () => this.#listeners.delete(listener);
	}
}
