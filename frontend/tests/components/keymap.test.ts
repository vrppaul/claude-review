import { describe, it, expect, beforeEach } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { FIELD_KEYS } from '$lib/components/keymap';
import type { Review } from '$lib/review/review.svelte';
import { A_LATER_TAKE, contextLine, diffFile, hunk } from '../diff';
import { broughtIntoView } from '../elements';
import { newComment } from '../new-comment';
import { openReview } from '../review';
import { storyHeld, toldChapter, toldStep } from '../story';

const files = ['a.py', 'b.py'].map((path) => diffFile({ path, hunks: [hunk([contextLine(1, 1, `in ${path}`)])] }));

let review: Review;

beforeEach(() => {
	review = openReview({ files, facts: { answerer_attached: true } });
});

/** What the help lists while it is open, row by row: the keys as it writes them, and what it says they do. */
function listedInTheHelp(): string[] {
	const list = within(screen.getByTestId('shortcuts-list'));
	const does = list.getAllByRole('definition').map((said) => said.textContent);
	return list.getAllByRole('term').map((keys, row) => `${keys.textContent}: ${does[row]}`);
}

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
		const first = broughtIntoView(sectionOf('a.py'));
		const second = broughtIntoView(sectionOf('b.py'));

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

	it('folds the file the reader is in by u, and unfolds it by u again', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		within(sectionOf('b.py')).getByTestId('line-gutter').focus();
		await user.keyboard('u');
		expect(review.reading.isFolded('b.py')).toBe(true);
		expect(review.reading.isFolded('a.py')).toBe(false);

		within(sectionOf('b.py')).getByRole('button', { expanded: false }).focus();
		await user.keyboard('u');
		expect(review.reading.isFolded('b.py')).toBe(false);
	});

	it('puts the file tree away by f, and brings it back by f again', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const shownAtFirst = review.layout.fileTree.open;

		await user.keyboard('f');
		expect(review.layout.fileTree.open).toBe(!shownAtFirst);

		await user.keyboard('f');
		expect(review.layout.fileTree.open).toBe(shownAtFirst);
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

	it('lists in the help what every key of the files does, and no key of another view', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');

		expect(listedInTheHelp()).toEqual([
			'j / k: Down / up a line',
			'Enter: Comment on this line',
			'Ctrl+Enter: Add the comment, or send the message, being written',
			'] / [: Next / previous file',
			'n / p: Next / previous comment',
			'a: Next unread reply',
			'c: Talk to the agent',
			'f: Show or hide the file tree',
			'v: Mark this file viewed',
			'u: Fold or unfold this file',
			'Ctrl+Shift+Enter: Finish the review',
			'?: Show this list',
			'Esc: Close it'
		]);
	});

	it('closes the help on ? as it opened it', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');
		await user.keyboard('?');

		expect(screen.queryByTestId('shortcuts-list')).toBeNull();
	});

	it('leaves a chord to an input method composing a word', async () => {
		render(ReviewScreen, { props: { review } });

		await fireEvent.keyDown(window, { key: 'Enter', ctrlKey: true, shiftKey: true, isComposing: true });

		expect(review.submission.finishing).toBe(false);
	});

	it('lists in the help the chord a comment or a message is sent from its field with', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');

		expect(screen.getByTestId('shortcuts-list').textContent).toContain(FIELD_KEYS);
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

describe('the keys of a review read as its story', () => {
	// A story of one chapter that tells a line of a.py, then a line of b.py
	const TOLD = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('a.py', 1), toldStep('b.py', 1)])] });

	beforeEach(() => {
		review = openReview({ files, story: TOLD, facts: { answerer_attached: true } });
		review.views.choose('story');
	});

	it('take the reader to the next piece of the story, and the previous, from the one they are in', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const [first, second] = screen.getAllByTestId('story-piece');
		const toTheFirst = broughtIntoView(first);
		const toTheSecond = broughtIntoView(second);

		within(first).getByTestId('line-gutter').focus();
		await user.keyboard(']');
		expect(toTheSecond).toHaveBeenCalled();

		within(second).getByTestId('line-gutter').focus();
		// A bracket is written twice to be typed once: one alone opens a key's name
		await user.keyboard('[[');
		expect(toTheFirst).toHaveBeenCalled();
	});

	it('take the reader on from the last step to what the story leaves out', async () => {
		const user = userEvent.setup();
		const leftOutOfA = { piece: toldStep('a.py', 5).piece, changed_lines: 1 };
		const story = storyHeld({ ...TOLD.story, left_out: [leftOutOfA] });
		review = openReview({ files, story, facts: { answerer_attached: true } });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });
		const [, lastStep, whatIsLeftOut] = screen.getAllByTestId('story-piece');
		const toWhatIsLeftOut = broughtIntoView(whatIsLeftOut);

		within(lastStep).getByTestId('line-gutter').focus();
		await user.keyboard(']');

		expect(toWhatIsLeftOut).toHaveBeenCalled();
	});

	it('leave the tree of files as the reader left it: f in a story is a key of its contents', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const treeOpen = review.layout.fileTree.open;

		await user.keyboard('f');

		expect(review.layout.fileTree.open).toBe(treeOpen);
	});

	it('put the contents beside the story away with f, and bring them back with it', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const shownAtFirst = review.layout.storyContents.open;

		await user.keyboard('f');
		expect(review.layout.storyContents.open).toBe(!shownAtFirst);

		await user.keyboard('f');
		expect(review.layout.storyContents.open).toBe(shownAtFirst);
	});

	it('leave the contents as the reader left them while no story has been told: there are none to put away', async () => {
		const user = userEvent.setup();
		review = openReview({ files, facts: { answerer_attached: true } });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });
		const shownAtFirst = review.layout.storyContents.open;

		await user.keyboard('f');

		expect(review.layout.storyContents.open).toBe(shownAtFirst);
	});

	it('mark no file viewed and fold none: v and u are keys of the files', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const [first] = screen.getAllByTestId('story-piece');

		within(first).getByTestId('line-gutter').focus();
		await user.keyboard('vu');

		expect(review.reading.isViewed('a.py')).toBe(false);
		expect(review.reading.isFolded('a.py')).toBe(false);
	});

	it("are listed in the help by what each does: every key the story shares with the files, and none that are the files' own", async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');

		expect(listedInTheHelp()).toEqual([
			'j / k: Down / up a line',
			'Enter: Comment on this line',
			'Ctrl+Enter: Add the comment, or send the message, being written',
			'] / [: Next / previous piece of the story',
			'n / p: Next / previous comment',
			'a: Next unread reply',
			'c: Talk to the agent',
			'f: Show or hide the contents',
			'Ctrl+Shift+Enter: Finish the review',
			'?: Show this list',
			'Esc: Close it'
		]);
	});

	it('are listed without those of a line, a piece, a comment or the contents while no story has been told: nothing of one is drawn', async () => {
		const user = userEvent.setup();
		review = openReview({ files, facts: { answerer_attached: true } });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');

		expect(listedInTheHelp()).toEqual([
			'Ctrl+Enter: Add the comment, or send the message, being written',
			'a: Next unread reply',
			'c: Talk to the agent',
			'Ctrl+Shift+Enter: Finish the review',
			'?: Show this list',
			'Esc: Close it'
		]);
	});

	it('are listed without Enter and n / p in a story the code has moved on from: its lines take no comment, and it draws none', async () => {
		const user = userEvent.setup();
		const toldOfAnotherTake = storyHeld(TOLD.story, { take: A_LATER_TAKE });
		review = openReview({ files, story: toldOfAnotherTake, facts: { answerer_attached: true } });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		await user.keyboard('?');

		expect(listedInTheHelp()).toEqual([
			'j / k: Down / up a line',
			'Ctrl+Enter: Add the comment, or send the message, being written',
			'] / [: Next / previous piece of the story',
			'a: Next unread reply',
			'c: Talk to the agent',
			'f: Show or hide the contents',
			'Ctrl+Shift+Enter: Finish the review',
			'?: Show this list',
			'Esc: Close it'
		]);
	});
});
