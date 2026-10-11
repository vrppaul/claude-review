import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
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

	it('takes the keyboard to the thread n brings into view', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'b.py', body: 'Why?' }));
		render(ReviewScreen, { props: { review } });

		await user.keyboard('n');

		expect(document.activeElement).toBe(within(sectionOf('b.py')).getByTestId('comment-thread'));
	});

	it('acts on the file of the thread n landed on, not on the one in view before', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'b.py', body: 'Why?' }));
		render(ReviewScreen, { props: { review } });

		await user.keyboard('n');
		await user.keyboard('v');

		expect(review.reading.isViewed('b.py')).toBe(true);
		expect(review.reading.isViewed('a.py')).toBe(false);
	});

	it('goes on from the thread the keyboard is on to the line below it, not back to the top', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		render(ReviewScreen, { props: { review } });

		await user.keyboard('n');
		await user.keyboard('j');

		expect(document.activeElement).toBe(within(sectionOf('b.py')).getByTestId('line-gutter'));
	});

	it('goes up from the thread the keyboard is on to the line above it', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'b.py', body: 'Why?' }));
		render(ReviewScreen, { props: { review } });

		await user.keyboard('n');
		await user.keyboard('k');

		expect(document.activeElement).toBe(within(sectionOf('b.py')).getByTestId('line-gutter'));
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

	it('leaves no cursor waiting when nobody is listening, for an agent arriving later to take', async () => {
		const user = userEvent.setup();
		review = openReview({ files, facts: { answerer_attached: false } });
		render(ReviewScreen, { props: { review } });
		await user.keyboard('c');
		expect(review.layout.agentPanel.open).toBe(true);
		expect(review.layout.agentPanel.inputWanted).toBe(false);

		await user.click(within(sectionOf('a.py')).getByTestId('line-gutter'));
		await user.keyboard('Half');
		review.answerer.setAttached(true);
		flushSync();

		expect(screen.getByTestId('panel-input')).toBeTruthy();
		expect(document.activeElement).toBe(screen.getByTestId('comment-input'));
	});

	it('never takes the keyboard from a field being typed in as the panel draws its own', async () => {
		const user = userEvent.setup();
		review = openReview({ files, facts: { answerer_attached: false } });
		review.layout.agentPanel.setOpen(true);
		render(ReviewScreen, { props: { review } });
		await user.click(within(sectionOf('a.py')).getByTestId('line-gutter'));
		review.layout.agentPanel.askForInput();

		review.answerer.setAttached(true);
		flushSync();

		expect(document.activeElement).toBe(screen.getByTestId('comment-input'));
		expect(review.layout.agentPanel.inputWanted).toBe(false);
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

	it('leaves a key pressed with Ctrl alone, or with Alt, to the browser', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const treeOpen = review.layout.fileTree.open;

		await user.keyboard('{Control>}f{/Control}');
		await user.keyboard('{Alt>}f{/Alt}');

		expect(review.layout.fileTree.open).toBe(treeOpen);
	});

	it('opens the help over a pane the keyboard is in, and leaves the pane open under it', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		await user.click(screen.getByTestId('settings-toggle'));
		expect(screen.getByTestId('settings-menu').contains(document.activeElement)).toBe(true);

		await user.keyboard('?');

		expect(screen.getByTestId('help-dialog')).toBeTruthy();
		expect(screen.getByTestId('settings-menu')).toBeTruthy();
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
