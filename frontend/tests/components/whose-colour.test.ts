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

// What a colour means, by the class that draws it: the stylesheet gives each
// its token, and these are the marks jsdom can see were given the right one
const AGENT_CHIP = 'cr-thread-chip-agent';
const UNREAD = 'text-(--cr-unread)';
const UNREAD_DOT = 'bg-(--cr-unread)';
const CONTROL = 'text-(--cr-control)';
const AT_WORK = 'bg-(--cr-agent)';
const READY = 'bg-(--cr-done)';

const file = diffFile({ path: 'src/routes.py', hunks: [hunk([addedLine(2, 'y = 3')])] });

/** A review an agent is answering. */
function answeredReview(): Review {
	return openReview({ files: [file], facts: { answerer_attached: true } });
}

describe('a colour says whose a thing is', () => {
	it('draws the files the agent names, in what it says and in what it works on, in its own colour', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.conversation.receive(null, 'Both halves are here.', ['src/routes.py']);
		review.answerer.showWork(work({ files: ['src/routes.py'] }));

		const { getByTestId } = render(AgentPanel, inReview(review));
		await tick();

		expect(getByTestId('answer-file').classList).toContain(AGENT_CHIP);
		expect(getByTestId('progress-file').classList).toContain(AGENT_CHIP);
	});

	it('draws a thread the agent mentions in what it says in its own colour', async () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.conversation.receive(null, 'See @src/routes.py:2-2', []);

		const { getByTestId } = render(AgentPanel, inReview(review));
		await tick();

		expect(getByTestId('answer-thread').classList).toContain(AGENT_CHIP);
	});

	it('draws a thread the agent raised, as the panel notes it, in its own colour', () => {
		const review = answeredReview();
		const anchor = lineAnchor('src/routes.py', 'new', 2, 2, ['y = 3']);
		review.threads.raise('raised-1', anchor, 'Is this on purpose?', 'question');
		review.conversation.note(raisedNote(anchor), ['raised-1']);

		const { getByTestId } = render(AgentPanel, inReview(review));

		expect(getByTestId('panel-thread-ref').classList).toContain(AGENT_CHIP);
	});

	it('draws a thread the reader pointed at in their own colour, not the agent’s', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.conversation.composer.setText('Look at @src/routes.py:2-2');
		await review.conversation.send(review.threads.all);

		const { getByTestId } = render(AgentPanel, inReview(review));

		expect(getByTestId('panel-thread-ref').classList).toContain('cr-thread-chip');
		expect(getByTestId('panel-thread-ref').classList).not.toContain(AGENT_CHIP);
	});

	it('says an answer nobody has read in the colour of what is unread, in the thread and in the list of replies', () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		const [thread] = review.threads.all;
		review.threads.receiveReply(thread.id, 'Because the caller retries.', null);

		const inThread = render(CommentThread, inReview(review, { thread: review.threads.all[0] }));
		const inList = render(RepliesMenu, inReview(review));

		expect(inThread.getByTestId('comment-unread').classList).toContain(UNREAD);
		expect(inList.getByTestId('unread-count').classList).toContain(UNREAD);
	});

	it('marks a row of the list of replies nobody has read with the unread colour', async () => {
		const review = answeredReview();
		review.threads.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why here?' }));
		review.threads.receiveReply(review.threads.all[0].id, 'Because the caller retries.', null);

		const { getByTestId } = render(RepliesMenu, inReview(review));
		getByTestId('replies-menu').click();
		await tick();

		const marks = [...getByTestId('reply-row').querySelectorAll('span')];
		expect(marks.some((mark) => mark.classList.contains(UNREAD_DOT))).toBe(true);
	});

	it('draws the keys in the help as controls', () => {
		const review = answeredReview();

		const { getByTestId } = render(HelpDialog, inReview(review));

		const keys = getByTestId('shortcuts-list').querySelectorAll('dt');
		expect(keys.length).toBeGreaterThan(0);
		for (const key of keys) expect(key.classList).toContain(CONTROL);
	});

	it('draws an agent listening in the colour of something ready', () => {
		const review = answeredReview();

		const { container } = render(PresenceDot, inReview(review));

		expect(container.querySelector('span')?.classList).toContain(READY);
	});

	it('draws the agent at work on a message in its own colour', async () => {
		listeningToThePanel();
		const review = answeredReview();
		review.conversation.composer.setText('Run the tests');
		await review.conversation.send([]);

		const { container } = render(PresenceDot, inReview(review));

		expect(container.querySelector('span')?.classList).toContain(AT_WORK);
	});
});
