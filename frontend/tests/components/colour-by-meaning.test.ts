import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import AgentPanel from '$lib/components/AgentPanel.svelte';
import CommentThread from '$lib/components/CommentThread.svelte';
import HelpDialog from '$lib/components/HelpDialog.svelte';
import PresenceDot from '$lib/components/PresenceDot.svelte';
import RepliesMenu from '$lib/components/RepliesMenu.svelte';
import { lineAnchor } from '$lib/anchors/line';
import { raisedNote } from '$lib/review/panel-notes';
import type { Review } from '$lib/review/review.svelte';
import { work } from '../agent-work';
import { addedLine, diffFile, hunk } from '../diff';
import { listeningToThePanel } from '../fake-server';
import { newComment } from '../new-comment';
import { inReview, openReview } from '../review';
import { colourDrawn, type Drawn, paint, THEMES } from '../stylesheets';
import { chatPush } from '../pushes';

// The colour of each meaning, by the token it is written once in: violet is
// the agent's — what it raised, said or brought the reader to, and what of
// it is not read yet; blue is the reader's — their marks in words, and the
// controls they act with; green, beside what the diff added, is what is done
const AGENTS = '--cr-agent';
const READERS_WORDS = '--cr-mark-text';
const READERS_CONTROLS = '--cr-mark';
const DONE = '--cr-add-text';
// And nothing in particular: the quiet ground of a dot saying nobody is there
const NOBODY = '--color-base-300';

/** That a part of an element is drawn in a meaning's colour, in every theme, whatever token stands between. */
function expectDrawnIn(element: Element | null | undefined, drawn: Drawn, meaning: string): void {
	if (!element) throw new Error('nothing is drawn');
	for (const theme of THEMES) expect(colourDrawn(element, drawn, theme), theme).toEqual(paint(meaning, theme));
}

const file = diffFile({ path: 'src/routes.py', hunks: [hunk([addedLine(2, 'y = 3')])] });

/** A review an agent is answering. */
function answeredReview(): Review {
	return openReview({ files: [file], facts: { answerer_attached: true } });
}

describe('each thing is drawn in the colour of what it means', () => {
	it('draws the files the agent names, in what it says and in what it works on, in its own colour', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.conversation.receive(chatPush('Both halves are here.', { files: ['src/routes.py'] }));
		review.answerer.showWork(work({ files: ['src/routes.py'] }));

		const { getByTestId } = render(AgentPanel, inReview(review));
		await tick();

		expectDrawnIn(getByTestId('answer-file'), 'color', AGENTS);
		expectDrawnIn(getByTestId('progress-file'), 'color', AGENTS);
	});

	it('draws a thread the agent mentions in what it says in its own colour', async () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.conversation.receive(chatPush('See @src/routes.py:2-2'));

		const { getByTestId } = render(AgentPanel, inReview(review));
		await tick();

		expectDrawnIn(getByTestId('answer-thread'), 'color', AGENTS);
	});

	it('draws a thread the agent raised, as the panel notes it, in its own colour', () => {
		const review = answeredReview();
		const anchor = lineAnchor('src/routes.py', 'new', 2, 2, ['y = 3']);
		review.threads.raise('raised-1', anchor, 'Is this on purpose?', 'question');
		review.conversation.note(raisedNote(anchor), ['raised-1']);

		const { getByTestId } = render(AgentPanel, inReview(review));

		expectDrawnIn(getByTestId('panel-thread-ref'), 'color', AGENTS);
	});

	it('draws a thread the reader pointed at in their own colour, not the agent’s', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.conversation.composer.setText('Look at @src/routes.py:2-2');
		await review.conversation.send(review.threads.all);

		const { getByTestId } = render(AgentPanel, inReview(review));

		expectDrawnIn(getByTestId('panel-thread-ref'), 'color', READERS_WORDS);
	});

	it('says an answer nobody has read in the colour of what is unread, in the thread and in the list of replies', () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		const [thread] = review.threads.all;
		review.threads.receiveReply(thread.id, 'Because the caller retries.', null);

		const inThread = render(CommentThread, inReview(review, { thread: review.threads.all[0] }));
		const inList = render(RepliesMenu, inReview(review));

		expectDrawnIn(inThread.getByTestId('comment-unread'), 'color', AGENTS);
		expectDrawnIn(inList.getByTestId('unread-count'), 'color', AGENTS);
	});

	it('marks a row of the list of replies nobody has read with the unread colour', async () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.threads.receiveReply(review.threads.all[0].id, 'Because the caller retries.', null);

		const { getByTestId } = render(RepliesMenu, inReview(review));
		getByTestId('replies-menu').click();
		await tick();

		const dot = [...getByTestId('reply-row').querySelectorAll('span')].find((mark) =>
			mark.classList.contains('rounded-full')
		);
		expectDrawnIn(dot, 'background', AGENTS);
	});

	it('draws the keys in the help as controls', () => {
		const review = answeredReview();

		const { getByTestId } = render(HelpDialog, inReview(review));

		const keys = getByTestId('shortcuts-list').querySelectorAll('dt');
		expect(keys.length).toBeGreaterThan(0);
		for (const key of keys) expectDrawnIn(key, 'color', READERS_CONTROLS);
	});

	it('draws an agent listening in the colour of something ready', () => {
		const review = answeredReview();

		const { container } = render(PresenceDot, inReview(review));

		expectDrawnIn(container.querySelector('span'), 'background', DONE);
	});

	it('draws an agent as nobody while the review cannot be reached: the page cannot know it is still there', () => {
		const review = answeredReview();
		review.link.lost();

		const { container } = render(PresenceDot, inReview(review));

		expectDrawnIn(container.querySelector('span'), 'background', NOBODY);
	});

	it('draws no agent as nobody', () => {
		const review = openReview({ files: [file] });

		const { container } = render(PresenceDot, inReview(review));

		expectDrawnIn(container.querySelector('span'), 'background', NOBODY);
	});

	it('draws the agent at work on a message in its own colour', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.conversation.composer.setText('Run the tests');
		await review.conversation.send([]);

		const { container } = render(PresenceDot, inReview(review));

		expectDrawnIn(container.querySelector('span'), 'background', AGENTS);
	});
});
