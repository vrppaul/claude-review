import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { KEYMAP } from '$lib/components/keymap';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, hunk } from '../diff';
import { newComment } from '../new-comment';
import { openReview } from '../review';

const files = ['a.py', 'b.py'].map((path) => diffFile({ path, hunks: [hunk([contextLine(1, 1, `in ${path}`)])] }));

let review: Review;

beforeEach(() => {
	review = openReview({ files, facts: { answerer_attached: true } });
});

/** The section a file is drawn in. */
function sectionOf(path: string): HTMLElement {
	const section = screen.getAllByTestId('file-section').find((candidate) => candidate.dataset.path === path);
	if (!section) throw new Error(`${path} is not drawn`);
	return section;
}

describe('the keys the review answers', () => {
	it('takes the reader to the next file, and the previous, from the one they are in', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const first = vi.spyOn(sectionOf('a.py'), 'scrollIntoView');
		const second = vi.spyOn(sectionOf('b.py'), 'scrollIntoView');

		within(sectionOf('a.py')).getByTestId('line-gutter').focus();
		await user.keyboard(']');
		expect(second).toHaveBeenCalled();

		within(sectionOf('b.py')).getByTestId('line-gutter').focus();
		await user.keyboard('[[');
		expect(first).toHaveBeenCalled();
	});

	it('goes to the oldest answer nobody has read, and reads it', async () => {
		const user = userEvent.setup();
		const id = review.threads.add(newComment({ file: 'b.py', body: 'Why?' }));
		review.threads.receiveReply(id, 'Because.', null);
		render(ReviewScreen, { props: { review } });

		await user.keyboard('a');

		expect(review.threads.unread).toHaveLength(0);
	});

	it('opens the panel with the cursor in it', async () => {
		const user = userEvent.setup();
		review.layout.agentPanel.setOpen(false);
		render(ReviewScreen, { props: { review } });

		await user.keyboard('c');

		expect(document.activeElement).toBe(screen.getByTestId('panel-input'));
	});

	it('leaves a letter typed in a field to the field', async () => {
		const user = userEvent.setup();
		review.layout.agentPanel.setOpen(true);
		render(ReviewScreen, { props: { review } });
		const treeOpen = review.layout.fileTree.open;

		await user.type(screen.getByTestId('panel-input'), 'f');

		expect(review.layout.fileTree.open).toBe(treeOpen);
	});

	it('lists in the help every key it answers, and closes the help on ? as it opened it', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');
		const listed = screen.getByTestId('shortcuts-list').textContent ?? '';
		for (const row of KEYMAP) expect(listed).toContain(row.keys);
		await user.keyboard('?');

		expect(screen.queryByTestId('shortcuts-list')).toBeNull();
	});

	it('answers no key of its own while the help is open over it', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const treeOpen = review.layout.fileTree.open;

		await user.keyboard('?');
		await user.keyboard('f');

		expect(review.layout.fileTree.open).toBe(treeOpen);
	});
});
