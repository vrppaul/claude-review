import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { FeedbackIssue, FeedbackRequest, ReviewResponse } from '$lib/types';
import { said } from '../elements';
import { listeningToThePanel, type FakeServer } from '../fake-server';
import { guideServer } from '../guide-server';
import { AGENT_ATTACHED, openReview } from '../review';
import { settled } from '../settled';

// The release serving the review, which the reader was shown already: no card of the guide's stands in the corner
const RELEASE = '1.5.0';
const WORDS = 'The tree forgets a folder I folded.';
const TITLE = 'Bug: The tree forgets a folder I folded.';
// The address an issue opens at on GitHub
const ADDRESS = 'https://github.com/vrppaul/claude-review/issues/new?title=Bug';

/**
 * The issue a server writes of what the page sent: its body says the words and the rows sent ticked, so a test
 * reads off the page what reached the server; filled in or too long to be, as the test says.
 */
function issueFrom(sent: FeedbackRequest, filled: boolean): FeedbackIssue {
	return {
		title: TITLE,
		body: `${sent.words}\n\ngoing: ${sent.going.join(', ')}`,
		with_it: { machine: 'claude-review 1.5.0, Linux, Chrome 141', reading: 'Files', part: null },
		address: ADDRESS,
		filled,
		for_agent: `Feedback on claude-review, a bug. ${sent.words}`
	};
}

/** A server that keeps how far the reader was shown around, and writes the issue of their feedback. */
function serving(filled = true): FakeServer {
	const server = guideServer(RELEASE);
	server.answerWith('POST /api/feedback', (request) => issueFrom(request.body as FeedbackRequest, filled));
	return server;
}

/** Draw a review, open Help and its Send feedback, and write the words: the card on its first step. */
async function writtenFeedback(
	user: ReturnType<typeof userEvent.setup>,
	facts: Partial<ReviewResponse> = {}
): Promise<void> {
	const review = openReview({ facts: { release: RELEASE, ...facts } });
	await review.guide.open();
	render(ReviewScreen, { props: { review } });
	await user.click(screen.getByTestId('open-help'));
	await user.click(screen.getByTestId('send-feedback'));
	await user.type(screen.getByTestId('feedback-words'), WORDS);
}

describe('feedback on the review itself', () => {
	it('opens from Help with the keyboard in its field, and keeps what was written once put away', async () => {
		serving();
		const user = userEvent.setup();
		await writtenFeedback(user);
		expect(document.activeElement).toBe(screen.getByTestId('feedback-words'));

		await user.click(screen.getByTestId('feedback-close'));
		await user.click(screen.getByTestId('open-help'));
		expect(said(screen.getByTestId('send-feedback'))).toContain('draft kept');
		await user.click(screen.getByTestId('send-feedback'));

		expect(screen.getByTestId<HTMLTextAreaElement>('feedback-words').value).toBe(WORDS);
	});

	it('opens on what is written once the news took the corner from where the last feedback went', async () => {
		serving();
		const user = userEvent.setup();
		await writtenFeedback(user);
		await user.click(screen.getByTestId('feedback-preview'));
		await settled();
		await user.click(screen.getByTestId('feedback-open-on-github'));

		await user.click(screen.getByTestId('open-help'));
		await user.click(screen.getByTestId('read-news'));
		await user.click(screen.getByTestId('guide-news-close'));
		await user.click(screen.getByTestId('open-help'));
		await user.click(screen.getByTestId('send-feedback'));

		expect(screen.getByTestId<HTMLTextAreaElement>('feedback-words').value).toBe('');
	});

	it('says why the issue could not be written, and keeps the words to try again', async () => {
		const server = guideServer(RELEASE);
		server.refuse('POST /api/feedback', 422, 'words: too long');
		const user = userEvent.setup();
		await writtenFeedback(user);

		await user.click(screen.getByTestId('feedback-preview'));
		await settled();

		expect(said(screen.getByTestId('feedback-failed'))).toContain('words: too long');
		expect(screen.getByTestId<HTMLTextAreaElement>('feedback-words').value).toBe(WORDS);
	});

	it('takes the part pressed while pointing, named by its test ids, and the page never hears the press', async () => {
		const server = serving();
		const user = userEvent.setup();
		await writtenFeedback(user);

		await user.click(screen.getByTestId('feedback-point'));
		await user.click(screen.getByTestId('open-help'));
		expect(screen.queryByTestId('shortcuts-list')).toBeNull();
		await user.click(screen.getByTestId('feedback-preview'));
		await settled();

		const [sent] = server.bodiesSentTo('POST /api/feedback') as FeedbackRequest[];
		expect(sent.part?.name).toMatch(/ › open-help$/);
	});

	it('takes the part the keyboard is on at Enter, and stops pointing at Escape', async () => {
		serving();
		const user = userEvent.setup();
		await writtenFeedback(user);

		await user.click(screen.getByTestId('feedback-point'));
		screen.getByTestId('open-help').focus();
		await user.keyboard('{Enter}');
		expect(said(screen.getByTestId('feedback-part'))).toMatch(/ › open-help$/);
		await user.click(screen.getByTestId('feedback-point-again'));
		await user.keyboard('{Escape}');
		await user.click(screen.getByTestId('open-help'));

		expect(screen.getByTestId('shortcuts-list')).toBeTruthy();
	});

	it('answers its own toggle while pointing, and gives the keyboard to it once a part is left out', async () => {
		serving();
		const user = userEvent.setup();
		await writtenFeedback(user);
		await user.click(screen.getByTestId('feedback-point'));
		await user.click(screen.getByTestId('feedback-point'));
		await user.click(screen.getByTestId('open-help'));
		expect(screen.getByTestId('shortcuts-list')).toBeTruthy();
		await user.keyboard('{Escape}');

		await user.click(screen.getByTestId('feedback-point'));
		screen.getByTestId('open-help').focus();
		await user.keyboard('{Enter}');
		screen.getByTestId('feedback-part-remove').focus();
		await user.keyboard('{Enter}');
		await settled();

		expect(document.activeElement).toBe(screen.getByTestId('feedback-point'));
	});

	it('shows the issue the review wrote, to the letter, and writes it again without a row the reader unticks', async () => {
		const server = serving();
		const user = userEvent.setup();
		await writtenFeedback(user);

		await user.click(screen.getByTestId('feedback-preview'));
		await settled();
		expect(said(screen.getByTestId('feedback-issue'))).toBe(`${TITLE} ${WORDS} going: machine, reading, part`);
		await user.click(screen.getByTestId('feedback-goes-machine'));
		await settled();

		expect(said(screen.getByTestId('feedback-issue'))).toBe(`${TITLE} ${WORDS} going: reading, part`);
		expect(server.bodiesSentTo('POST /api/feedback')).toHaveLength(2);
	});

	it('copies the text of an issue too long to open filled in, and says so', async () => {
		serving(false);
		const user = userEvent.setup();
		await writtenFeedback(user);
		await user.click(screen.getByTestId('feedback-preview'));
		await settled();

		await user.click(screen.getByTestId('feedback-open-on-github'));
		await settled();

		expect(await navigator.clipboard.readText()).toBe(`${WORDS}\n\ngoing: machine, reading, part`);
		expect(said(screen.getByTestId('feedback-too-long'))).toContain('the text is copied');
	});

	it("hands the issue to the agent as the reader's message in its panel, and forgets the draft", async () => {
		const server = serving();
		listeningToThePanel(server);
		const user = userEvent.setup();
		await writtenFeedback(user, AGENT_ATTACHED);
		await user.click(screen.getByTestId('feedback-preview'));
		await settled();

		await user.click(screen.getByTestId('feedback-hand-to-agent'));
		await settled();

		expect(server.bodiesSentTo('POST /api/message')).toMatchObject([
			{ body: `Feedback on claude-review, a bug. ${WORDS}`, threads: [], images: [] }
		]);
		expect(said(screen.getByTestId('feedback'))).toContain('Handed to the agent. It answers in its panel.');
		await user.click(screen.getByTestId('feedback-done'));
		await user.click(screen.getByTestId('open-help'));
		expect(said(screen.getByTestId('send-feedback'))).toBe('Send feedback');
	});
});
