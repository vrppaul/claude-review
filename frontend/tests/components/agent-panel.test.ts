import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import AgentPanel from '$lib/components/AgentPanel.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { panelStore } from '$lib/stores/panel.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import type { Comment } from '$lib/types';
import { addedLine, diffFile, hunk } from '../diff';
import { fakeServer, listeningToThePanel, UNPROCESSABLE } from '../fake-server';
import { newComment } from '../new-comment';
import {
	IMAGE_LIMITS,
	KEPT_AS,
	keepingImages,
	oversizedScreenshot,
	paste,
	screenshot
} from '../pasted-images';

const TITLE = 'claude-review: uncommitted changes';
// jsdom lays nothing out, so the panel is given a height to scroll in: this
// much on screen out of this much said
const VISIBLE_HEIGHT = 100;
const FULL_HEIGHT = 500;

const file = diffFile({ path: 'src/routes.py', hunks: [hunk([addedLine(2, 'y = 3')])] });

/** Write a message in the panel and send it, the way the composer does. */
function say(text: string, threads: Comment[] = []): Promise<void> {
	panelStore.setComposerText(text);
	return panelStore.send(threads);
}

function givenTall(element: HTMLElement) {
	Object.defineProperty(element, 'clientHeight', { value: VISIBLE_HEIGHT, configurable: true });
	Object.defineProperty(element, 'scrollHeight', { value: FULL_HEIGHT, configurable: true });
}

function painted(): Promise<void> {
	return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

describe('the agent panel', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff', TITLE);
		diffStore.setImageLimits(IMAGE_LIMITS);
		commentStore.restore(TITLE);
		panelStore.restore(TITLE);
		reviewStore.attachAnswerer();
	});

	it('says what it is for before anything has been said', () => {
		const { getByTestId } = render(AgentPanel);

		expect(getByTestId('panel-empty')).toBeTruthy();
		expect(getByTestId('panel-input')).toBeTruthy();
	});

	it('offers nothing to type into when nobody is listening', () => {
		// Nobody attached after all
		reviewStore.clear();

		const { getByTestId, queryByTestId } = render(AgentPanel);

		expect(getByTestId('panel-unattached')).toBeTruthy();
		expect(getByTestId('panel-read-only')).toBeTruthy();
		expect(queryByTestId('panel-input')).toBeNull();
	});

	it('keeps the commands for attaching by hand folded away', () => {
		// Nobody attached after all
		reviewStore.clear();

		const { getByTestId } = render(AgentPanel);

		// An agent that opened the review is about to attach; the reader
		// should not be met with setup instructions meant for somebody else
		expect((getByTestId('panel-attach-by-hand') as HTMLDetailsElement).open).toBe(false);
	});

	it('sends what was typed and empties the field', async () => {
		const user = userEvent.setup({ delay: null });
		const server = listeningToThePanel();

		const { getByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Run the tests');
		await user.click(getByTestId('send-message'));

		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([{ text: 'Run the tests' }]);
		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe('');
	});

	it('points at a thread by picking it, not by retyping which line it was', async () => {
		const user = userEvent.setup({ delay: null });
		commentStore.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why catch here?' }));

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Look at @');
		await user.click(getAllByTestId('thread-option')[0]);

		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe(
			'Look at @src/routes.py:2-2 '
		);
		expect(getByTestId('pointed-thread').textContent).toContain('routes.py');
	});

	it('points at a file nobody has commented on', async () => {
		const user = userEvent.setup({ delay: null });

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'What is in @');
		await user.click(getAllByTestId('file-option')[0]);

		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe(
			'What is in @src/routes.py '
		);
	});

	it('sends the thread the message points at', async () => {
		const user = userEvent.setup({ delay: null });
		const server = listeningToThePanel();
		commentStore.add(newComment({ file: 'src/routes.py', startLine: 2, body: 'Why catch here?' }));

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Look at @');
		await user.click(getAllByTestId('thread-option')[0]);
		await user.type(getByTestId('panel-input'), 'again');
		await user.click(getByTestId('send-message'));

		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([
			{ threads: [{ body: 'Why catch here?' }] }
		]);
	});

	it('offers to stop a message the agent is still working on', async () => {
		const user = userEvent.setup({ delay: null });
		const server = listeningToThePanel();

		const { getByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Never mind');
		await user.click(getByTestId('send-message'));

		expect(getByTestId('panel-working')).toBeTruthy();
		await user.click(getByTestId('stop-message'));

		expect(server.bodiesSentTo('POST /api/cancel')).toEqual([
			{ message_id: panelStore.turns[0].id }
		]);
		expect(getByTestId('panel-cancelled')).toBeTruthy();
	});

	it('brings a new turn into view', async () => {
		listeningToThePanel();
		const { getByTestId } = render(AgentPanel);
		const stream = getByTestId('panel-turns');
		givenTall(stream);

		await say('Run the tests');
		panelStore.receive(panelStore.turns[0].id, 'One failed; fixed and green.');
		await painted();

		expect(stream.scrollTop).toBe(FULL_HEIGHT);
	});

	it('leaves the reader where they are reading', async () => {
		listeningToThePanel();
		await say('Run the tests');

		const { getByTestId } = render(AgentPanel);
		const stream = getByTestId('panel-turns');
		givenTall(stream);
		// Scrolled up into what was said earlier
		stream.scrollTop = 0;
		stream.dispatchEvent(new Event('scroll'));

		panelStore.receive(panelStore.turns[0].id, 'One failed; fixed and green.');
		await painted();

		expect(stream.scrollTop).toBe(0);
	});

	it('says what is being done, not only that something is', async () => {
		const user = userEvent.setup({ delay: null });
		listeningToThePanel();

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Fix the scroll');
		await user.click(getByTestId('send-message'));

		panelStore.reportProgress(undefined, 'rewriting the answer handler', [
			'src/lib/components/AgentPanel.svelte'
		]);
		await tick();

		expect(getByTestId('panel-progress').textContent).toContain('rewriting the answer handler');
		expect(getAllByTestId('progress-file')[0].textContent).toContain('AgentPanel.svelte');
	});

	it('draws what the work branched into, and what is finished', async () => {
		const user = userEvent.setup({ delay: null });
		listeningToThePanel();

		const { getByTestId, getAllByTestId } = render(AgentPanel);
		await user.type(getByTestId('panel-input'), 'Find every caller');
		await user.click(getByTestId('send-message'));

		panelStore.reportProgress(undefined, 'looking for other callers', [], [
			{ text: 'ran the panel tests', done: true },
			{ text: 'three subagents out, one back', done: false }
		]);
		await tick();

		const steps = getAllByTestId('progress-steps')[0];
		expect(steps.textContent).toContain('ran the panel tests');
		expect(steps.textContent).toContain('three subagents out, one back');
	});

	it('takes the line away once the message it was about is answered', async () => {
		listeningToThePanel();
		await say('Fix the scroll');
		const asked = panelStore.turns[0].id;
		panelStore.reportProgress(asked, 'rewriting it', [], []);

		panelStore.receive(asked, 'Done, and green.');

		expect(panelStore.progress).toBeNull();
	});

	it('leaves work that is not what was answered still showing', async () => {
		listeningToThePanel();
		await say('Fix the scroll');
		// Work of the agent's own — four reviewers reading, a round being
		// worked through — belongs to no message and outlives any answer
		panelStore.reportProgress(undefined, 'four cold reviewers reading', [], []);

		panelStore.receive(panelStore.turns[0].id, 'Done, and green.');

		expect(panelStore.progress?.text).toBe('four cold reviewers reading');
	});

	it('shows work nobody is waiting on, in a row of its own', async () => {
		const { getByTestId } = render(AgentPanel);

		panelStore.reportProgress(undefined, 'taking the diff again', [], []);
		await tick();

		expect(getByTestId('panel-work')).toBeTruthy();
		expect(getByTestId('panel-progress').textContent).toContain('taking the diff again');
	});

	it('lets the agent speak first, with a file worth opening at it', async () => {
		const { getByTestId } = render(AgentPanel);

		panelStore.receive(undefined, 'Tests are green again.', ['src/claude_review/cli.py']);
		await tick();

		expect(getByTestId('panel-answer').textContent).toContain('Tests are green again.');
		expect(getByTestId('answer-file').textContent).toContain('cli.py');
	});

	it('tells the review it can weigh apart from the context only the agent knows', () => {
		panelStore.report({ model: 'opus-5', context: '53% of 1M', at: Date.now() });

		const { getByTestId } = render(AgentPanel);

		expect(getByTestId('review-weight').textContent).toContain('review ~');
		expect(getByTestId('agent-context').textContent).toContain('53% of 1M');
		expect(getByTestId('agent-context').textContent).toContain('as reported');
		expect(getByTestId('agent-model').textContent).toContain('opus-5');
	});

	it('shows no context at all rather than a number nobody reported', () => {
		const { queryByTestId, getByTestId } = render(AgentPanel);

		expect(getByTestId('review-weight')).toBeTruthy();
		expect(queryByTestId('agent-context')).toBeNull();
	});

	it('sends a pasted screenshot, by the id the server kept it under', async () => {
		const user = userEvent.setup({ delay: null });
		const server = keepingImages(listeningToThePanel());

		const { getByTestId, findByTestId, queryByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		expect((await findByTestId('attached-image')).getAttribute('src')).toBe(`/api/images/${KEPT_AS}`);
		// An image alone is a message: a screenshot can be the whole question
		await user.click(getByTestId('send-message'));

		expect(server.requestsTo('POST /api/images')).toHaveLength(1);
		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([{ images: [KEPT_AS] }]);
		expect(queryByTestId('attached-images')).toBeNull();
		expect(getByTestId('said-image').getAttribute('href')).toBe(`/api/images/${KEPT_AS}`);
	});

	it('takes an image off the message, and off the server', async () => {
		const user = userEvent.setup({ delay: null });
		const server = keepingImages(listeningToThePanel());

		const { getByTestId, findByTestId, queryByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await user.click(await findByTestId('detach-image'));

		expect(queryByTestId('attached-images')).toBeNull();
		expect((getByTestId('send-message') as HTMLButtonElement).disabled).toBe(true);
		expect(server.requests.at(-1)).toMatchObject({
			method: 'DELETE',
			path: `/api/images/${KEPT_AS}`
		});
	});

	it('keeps an image pasted while the last message was still on its way', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		// Each image kept under its number: the first pasted is 1.png
		server.answerWith('POST /api/images', () => ({
			image_id: `${server.requestsTo('POST /api/images').length}.png`
		}));
		// The message is held until the second image has landed
		const messages = server.hold('POST /api/message');

		const { getByTestId, findByTestId, getAllByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await findByTestId('attached-image');
		await user.click(getByTestId('send-message'));
		await paste(getByTestId('panel-input'), screenshot());
		await vi.waitFor(() => expect(getAllByTestId('attached-image')).toHaveLength(2));
		messages.answer(0, { status: 'sent' });

		await vi.waitFor(() => expect(getAllByTestId('attached-image')).toHaveLength(1));
		expect(getByTestId('attached-image').getAttribute('src')).toBe('/api/images/2.png');
	});

	it('says an image is gone rather than drawing a broken one', async () => {
		const user = userEvent.setup({ delay: null });
		keepingImages(listeningToThePanel());

		const { getByTestId, findByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await findByTestId('attached-image');
		await user.click(getByTestId('send-message'));
		// What a restarted review does to an image the old one kept
		await fireEvent.error(getByTestId('said-image-picture'));

		expect(getByTestId('lost-image').textContent).toContain('can no longer be shown');
	});

	it('says why an image was refused', async () => {
		fakeServer().refuse('POST /api/images', UNPROCESSABLE, 'The image is over 10 MB');

		const { getByTestId, findByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());

		expect((await findByTestId('panel-error')).textContent).toContain('over 10 MB');
	});

	it('keeps a half-written message and its images through a reload', async () => {
		keepingImages(listeningToThePanel());
		const { getByTestId, findByTestId, unmount } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await findByTestId('attached-image');
		panelStore.setComposerText('Look at this');
		unmount();

		panelStore.clear();
		panelStore.restore(TITLE);
		const reloaded = render(AgentPanel);

		expect((reloaded.getByTestId('panel-input') as HTMLTextAreaElement).value).toBe('Look at this');
		expect(reloaded.getByTestId('attached-image').getAttribute('src')).toBe(
			`/api/images/${KEPT_AS}`
		);
	});

	it('takes an image the server lost off the message, and says so', async () => {
		keepingImages(listeningToThePanel());

		const { getByTestId, findByTestId, queryByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await fireEvent.error(await findByTestId('attached-image'));

		expect(queryByTestId('attached-image')).toBeNull();
		expect(getByTestId('panel-error').textContent).toContain('could not be shown');
	});

	it('refuses an image over the limit without uploading it', async () => {
		const server = keepingImages(listeningToThePanel());

		const { getByTestId, findByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), oversizedScreenshot());

		expect((await findByTestId('panel-error')).textContent).toContain('over 10 MB');
		expect(server.requests).toEqual([]);
	});

	it('refuses an image past what one message takes', async () => {
		keepingImages(listeningToThePanel());
		diffStore.setImageLimits({ ...IMAGE_LIMITS, max_images_per_message: 1 });

		const { getByTestId, findByTestId, getAllByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), screenshot());
		await findByTestId('attached-image');
		await paste(getByTestId('panel-input'), screenshot());

		expect((await findByTestId('panel-error')).textContent).toContain('At most 1 images at a time');
		expect(getAllByTestId('attached-image')).toHaveLength(1);
	});

	it('leaves a paste of plain text to the field', async () => {
		const server = keepingImages(listeningToThePanel());

		const { getByTestId, queryByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'));

		expect(server.requests).toEqual([]);
		expect(queryByTestId('attached-images')).toBeNull();
	});

	it('keeps what was typed while the last message was on its way', async () => {
		const messages = fakeServer().hold('POST /api/message');

		const { getByTestId } = render(AgentPanel);
		panelStore.setComposerText('Fix this');
		const sending = panelStore.send([]);
		panelStore.setComposerText('Fix this and the next one');
		messages.answer(0, { status: 'sent' });
		await sending;

		expect(panelStore.turns.at(-1)?.body).toBe('Fix this');
		expect((getByTestId('panel-input') as HTMLTextAreaElement).value).toBe('and the next one');
	});

	it('does not let an image too large to send take the place of one that fits', async () => {
		keepingImages(listeningToThePanel());
		diffStore.setImageLimits({ ...IMAGE_LIMITS, max_images_per_message: 1 });

		const { getByTestId, findByTestId } = render(AgentPanel);
		await paste(getByTestId('panel-input'), oversizedScreenshot(), screenshot());

		expect((await findByTestId('panel-error')).textContent).toContain('over 10 MB');
		expect(getByTestId('attached-image').getAttribute('src')).toBe(`/api/images/${KEPT_AS}`);
	});
});
