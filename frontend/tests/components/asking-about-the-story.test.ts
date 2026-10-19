import { beforeEach, describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { storyAnchor } from '$lib/anchors/story';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { storyComment } from '../new-comment';
import { AGENT_ATTACHED, openReview } from '../review';
import { storyHeld, toldChapter, toldStep, toldStory } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one')])] })];
// What the overview says: the task, what was done, and what to doubt
const TASK = 'Let the reader paste a screenshot.';
const DONE = 'A pasted image goes to the review.';
const DOUBT = 'Whether an image is checked before it is kept.';
const TOLD = storyHeld({ overview: { ...toldStory().overview, task: TASK, done: DONE, doubt: DOUBT } });
// A story with every other kind of block: items in two of the overview's lists, a chapter's why and where
// to doubt it, and a step's reason
const DECISIONS = [
	{ text: 'Images are kept on disk.', chapter: null },
	{ text: 'They are known by their bytes.', chapter: null }
];
const TOLD_WHOLE = storyHeld({
	overview: { ...toldStory().overview, decisions: DECISIONS, later: [{ text: 'Dragging.', chapter: null }] },
	chapters: [toldChapter('ch-1', [toldStep('a.py', 1, 'The first line comes first.')], { doubt: 'Line one?' })]
});
// Each of those blocks: the test id of what draws it, which of those it is, and the block a thread on it hangs on
const EVERY_OTHER_BLOCK = [
	{
		called: 'the second decision',
		drawnIn: 'overview-item',
		nth: 1,
		block: { at: 'item', list: 'decisions', item: 1 }
	},
	{ called: 'a thing left for later', drawnIn: 'overview-item', nth: 2, block: { at: 'item', list: 'later', item: 0 } },
	{
		called: "a chapter's why",
		drawnIn: 'chapter-why-block',
		nth: 0,
		block: { at: 'chapter', chapter: 'ch-1', text: 'why' }
	},
	{
		called: 'where to doubt a chapter',
		drawnIn: 'chapter-doubt-block',
		nth: 0,
		block: { at: 'chapter', chapter: 'ch-1', text: 'doubt' }
	},
	{
		called: "a step's reason",
		drawnIn: 'step-reason-block',
		nth: 0,
		block: { at: 'reason', file: 'a.py', first_line: 1 }
	}
];

// The blocks whose words stand in a frame of their own, by the test id of what draws each
const FRAMED_BLOCKS = [
	{ called: "a chapter's why", drawnIn: 'chapter-why-block' },
	{ called: 'where to doubt a chapter', drawnIn: 'chapter-doubt-block' },
	{ called: "a step's reason", drawnIn: 'step-reason-block' }
];

let review: Review;

/** Ask about a block of the overview, by its test id, and write a comment on it. */
async function writeAbout(block: string, comment: string): Promise<ReturnType<typeof userEvent.setup>> {
	const user = userEvent.setup();
	await user.click(within(screen.getByTestId(block)).getByTestId('ask-about-this'));
	await user.type(screen.getByTestId('comment-input'), comment);
	return user;
}

describe("the overview's three lines", () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD, facts: AGENT_ATTACHED });
		review.views.choose('story');
	});

	it('each offer to be asked about', () => {
		render(ReviewScreen, { props: { review } });

		for (const block of ['overview-task', 'overview-done', 'overview-doubt']) {
			expect(within(screen.getByTestId(block)).getByTestId('ask-about-this').textContent).toContain('Ask about this');
		}
	});

	it('each name their offer by the line, so that whoever cannot see which line it stands over hears it', () => {
		render(ReviewScreen, { props: { review } });

		const names = ['overview-task', 'overview-done', 'overview-doubt'].map((block) =>
			within(screen.getByTestId(block)).getByTestId('ask-about-this').getAttribute('aria-label')
		);

		expect(names).toEqual([
			'Ask about this: Story · Task',
			'Ask about this: Story · Done',
			'Ask about this: Story · Doubt'
		]);
	});

	it('open a comment under the block asked about, headed by what the story heads it with, which may ask straight away', async () => {
		render(ReviewScreen, { props: { review } });

		await userEvent.setup().click(within(screen.getByTestId('overview-doubt')).getByTestId('ask-about-this'));

		const field = within(screen.getByTestId('overview-doubt')).getByTestId('comment-box');
		expect(within(field).getByText('Doubt')).toBeTruthy();
		expect(within(field).getByTestId('ask-now')).toBeTruthy();
	});

	it('invite a comment in the words of their offer', async () => {
		render(ReviewScreen, { props: { review } });

		await userEvent.setup().click(within(screen.getByTestId('overview-task')).getByTestId('ask-about-this'));

		expect(screen.getByTestId('comment-input').getAttribute('placeholder')).toBe('Ask about this…');
	});

	it('take a comment as a thread on the words of the block, drawn under it alone and named as the story heads it', async () => {
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-doubt', 'Is it checked at all?');
		await user.click(screen.getByTestId('save-comment'));

		expect(review.threads.all.map((thread) => thread.anchor)).toEqual([
			{ kind: 'story', block: { at: 'overview', text: 'doubt' }, quote: [DOUBT], outdated: false }
		]);
		const drawn = within(screen.getByTestId('overview-doubt')).getByTestId('comment-thread');
		expect(drawn.getAttribute('aria-label')).toBe('Thread on Story · Doubt');
		expect(within(screen.getByTestId('overview-task')).queryByTestId('comment-thread')).toBeNull();
	});

	it('hand a question on a block straight to the agent, with the words it is on', async () => {
		const server = fakeServer();
		server.answer('POST /api/ask', null);
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-task', 'Why only a screenshot?');
		await user.click(screen.getByTestId('ask-now'));

		expect(server.bodiesSentTo('POST /api/ask')).toMatchObject([
			{ thread: { anchor: { kind: 'story', block: { at: 'overview', text: 'task' }, quote: [TASK] } } }
		]);
	});

	it('put a comment away unsaid, and leave the block as it was', async () => {
		render(ReviewScreen, { props: { review } });

		const user = await writeAbout('overview-done', 'Not this one.');
		await user.click(screen.getByTestId('cancel-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));

		expect(screen.queryByTestId('comment-box')).toBeNull();
		expect(review.threads.all).toEqual([]);
	});
});

describe("the story's other blocks", () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD_WHOLE, facts: AGENT_ATTACHED });
		review.views.choose('story');
	});

	it.each(EVERY_OTHER_BLOCK)(
		'take a thread on $called, drawn under it and nowhere else',
		async ({ drawnIn, nth, block }) => {
			render(ReviewScreen, { props: { review } });
			// What more the overview lists stands folded away until the reader opens it
			await userEvent.setup().click(screen.getByTestId('story-more-toggle'));
			const asked = screen.getAllByTestId(drawnIn)[nth] as HTMLElement;

			await userEvent.setup().click(within(asked).getByTestId('ask-about-this'));
			await userEvent.setup().type(screen.getByTestId('comment-input'), 'Why so?');
			await userEvent.setup().click(screen.getByTestId('save-comment'));

			expect(review.threads.all.map((thread) => thread.anchor)).toMatchObject([{ kind: 'story', block }]);
			expect(within(asked).getAllByTestId('comment-thread')).toHaveLength(1);
			expect(screen.getAllByTestId('comment-thread')).toHaveLength(1);
		}
	);

	it.each(FRAMED_BLOCKS)(
		'hang what is written on $called, and its thread, below the frame the words stand in',
		async ({ drawnIn }) => {
			render(ReviewScreen, { props: { review } });
			const asked = screen.getByTestId(drawnIn);
			const frame = within(asked).getByTestId(`${drawnIn}-frame`);

			await userEvent.setup().click(within(asked).getByTestId('ask-about-this'));
			expect(within(asked).getByTestId('comment-box')).toBeTruthy();
			expect(within(frame).queryByTestId('comment-box')).toBeNull();
			await userEvent.setup().type(screen.getByTestId('comment-input'), 'Why so?');
			await userEvent.setup().click(screen.getByTestId('save-comment'));

			expect(within(asked).getAllByTestId('comment-thread')).toHaveLength(1);
			expect(within(frame).queryByTestId('comment-thread')).toBeNull();
		}
	);

	it('name their offers by their chapter or their step too, so that no two chapters offer alike', () => {
		render(ReviewScreen, { props: { review } });

		const names = ['chapter-why-block', 'chapter-doubt-block', 'step-reason-block'].map((block) =>
			within(screen.getByTestId(block)).getByTestId('ask-about-this').getAttribute('aria-label')
		);

		expect(names).toEqual([
			'Ask about this: ch-1 · Why',
			'Ask about this: ch-1 · Doubt',
			'Ask about this: a.py:1 · Reason'
		]);
	});

	it('keep the lists of the overview open while a thread hangs in them, though their heading is pressed', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const toggle = screen.getByTestId('story-more-toggle');
		await user.click(toggle);
		await user.click(within(screen.getAllByTestId('overview-item')[0]).getByTestId('ask-about-this'));
		await user.type(screen.getByTestId('comment-input'), 'Why on disk?');
		await user.click(screen.getByTestId('save-comment'));

		await user.click(toggle);

		expect(toggle.getAttribute('aria-expanded')).toBe('true');
		expect(screen.getAllByTestId('comment-thread')).toHaveLength(1);
	});

	it('offer nothing on the reason of a step of a file no thread can name', () => {
		const unnamable = { ...toldStep('a.py', 1, 'The first line comes first.'), commentable: false };
		review = openReview({ files, story: storyHeld({ chapters: [toldChapter('ch-1', [unnamable])] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('step-reason').textContent).toBe('The first line comes first.');
		expect(screen.queryByTestId('step-reason-block')).toBeNull();
	});
});

describe('no story held', () => {
	beforeEach(() => {
		// The review picked up a draft written on a story it does not hold: none has been told since it began
		review = openReview({ files, facts: AGENT_ATTACHED });
		review.threads.add(storyComment({ at: 'overview', text: 'doubt' }, 'Is it checked at all?'));
		review.views.choose('story');
	});

	it('stands a thread on the words of a story told before at the head of the story, above what the reader waits on', () => {
		render(ReviewScreen, { props: { review } });

		const head = screen.getByTestId('unplaced-threads');
		expect(within(head).getByTestId('comment-thread').textContent).toContain('Is it checked at all?');
		const waiting = screen.getByTestId('story-waiting');
		expect(head.compareDocumentPosition(waiting) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
	});

	it('takes the next thread key to a thread standing at its head', async () => {
		render(ReviewScreen, { props: { review } });

		await userEvent.setup().keyboard('n');

		expect(document.activeElement).toBe(within(screen.getByTestId('unplaced-threads')).getByTestId('comment-thread'));
	});
});

describe('a story told again', () => {
	it('stands a thread on words it says nowhere at its head, saying why, and under no block', () => {
		// The story told now says nothing to doubt: the thread was on what the story before said
		review = openReview({ files, story: storyHeld(), facts: AGENT_ATTACHED });
		const lost = { ...storyAnchor({ at: 'overview', text: 'doubt' }, DOUBT), outdated: true };
		review.threads.add({ ...storyComment(lost.block, 'Is it checked at all?'), anchor: lost });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const head = screen.getByTestId('unplaced-threads');
		expect(head.textContent).toContain('1 thread on words the story no longer says');
		expect(within(head).getByTestId('comment-thread').textContent).toContain('Is it checked at all?');
		expect(screen.getAllByTestId('comment-thread')).toHaveLength(1);
		const overview = screen.getByTestId('story-overview');
		expect(head.compareDocumentPosition(overview) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
	});
});
