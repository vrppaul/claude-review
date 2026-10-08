import type { CommentSeverity, LineSide, NewComment } from '$lib/types';
import { lineAnchor } from '$lib/anchors/line';

/** What a reader picks and writes when they comment on lines. */
interface Written {
	file: string;
	side: LineSide;
	startLine: number;
	endLine: number;
	quote: string[];
	body: string;
	severity: CommentSeverity;
	images: string[];
}

/** A comment as the reader writes one, with whatever a test does not care about filled in. */
export function newComment(written: Partial<Written> = {}): NewComment {
	const picked: Written = {
		file: 'file.ts',
		side: 'new',
		startLine: 1,
		endLine: written.startLine ?? 1,
		quote: [],
		body: 'A note',
		severity: 'note',
		images: [],
		...written
	};
	return {
		anchor: lineAnchor(picked.file, picked.side, picked.startLine, picked.endLine, picked.quote),
		body: picked.body,
		severity: picked.severity,
		images: picked.images
	};
}
