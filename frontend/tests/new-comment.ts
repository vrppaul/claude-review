import type { NewComment } from '$lib/types';

/** A comment as the reader writes one, with whatever a test does not care about filled in. */
export function newComment(written: Partial<NewComment> = {}): NewComment {
	return {
		file: 'file.ts',
		side: 'new',
		startLine: 1,
		endLine: 1,
		body: 'A note',
		severity: 'note',
		quote: [],
		images: [],
		...written
	};
}
