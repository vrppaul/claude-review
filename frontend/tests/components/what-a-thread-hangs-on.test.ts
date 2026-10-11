import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import CommentThread from '$lib/components/CommentThread.svelte';
import { lineAnchor } from '$lib/anchors/line';
import { contextLine, diffFile, hunk } from '../diff';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';

// What a kind of anchor says through its view, other than what a line
// anchor quotes: a thread draws what the view says, never what it reads off
// the anchor itself. Hoisted with the mock below, which runs first.
const viewSays = vi.hoisted(() => ({
	writtenAgainst: ['what the view says it was written against'],
	replaces: ['what the view says a suggestion replaces']
}));

vi.mock('$lib/anchors/views', async (importOriginal) => {
	const original = await importOriginal<typeof import('$lib/anchors/views')>();
	return {
		...original,
		anchorWrittenAgainst: () => viewSays.writtenAgainst,
		anchorReplaces: () => viewSays.replaces
	};
});

const file = diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x = 1')])] });

describe('a thread whatever it hangs on', () => {
	it('shows what its anchor says it was written against, once its place is gone, and what a suggestion replaces', () => {
		const review = openReview({ files: [file] });
		review.threads.add({
			...newComment({ file: 'a.py', body: 'Rather:\n\n```suggestion\nx = 2\n```' }),
			anchor: { ...lineAnchor('a.py', 'new', 1, 1, ['the quote on the anchor']), outdated: true }
		});
		const [thread] = review.threads.all;
		if (!thread) throw new Error('No thread was added');

		const { getByTestId } = render(CommentThread, inReview(review, { thread }));

		expect(getByTestId('stale-quote').textContent).toContain(viewSays.writtenAgainst[0]);
		expect(getByTestId('comment-suggestion').textContent).toContain(viewSays.replaces[0]);
		expect(getByTestId('comment-thread').textContent).not.toContain('the quote on the anchor');
	});
});
