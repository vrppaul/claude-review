import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { formatWeight } from '$lib/review/weight';
import { addedLine, diffFile, hunk } from '../diff';
import { said } from '../elements';
import { keepingSettings, takingStoryAskings, type FakeServer } from '../fake-server';
import { handOverNext } from '../pushes';
import { openReview, settingsWithStoriesOn, type Opened } from '../review';
import { settled } from '../settled';
import { ASKED, STOPPED, storyHeld, storyStanding, TAKEN, toldChapter, toldStep } from '../story';

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(9, 'nine')])] })];
// A story of the change, in two chapters
const IN_TWO_CHAPTERS = storyHeld({
	chapters: [toldChapter('ch-1', [toldStep('a.py', 1)]), toldChapter('ch-2', [toldStep('a.py', 9)])]
});

// What the review says of itself with an agent attached: the panel then offers its field
const AGENT_ATTACHED = { answerer_attached: true };

/** A server that keeps the reader's choices, and takes every story asked for or stopped. */
function serving(): FakeServer {
	const server = takingStoryAskings();
	keepingSettings(server);
	return server;
}

/** Draw a review of the change as the page opens it. */
function drawn(opened: Opened = {}): Review {
	const review = openReview({ files, ...opened });
	render(ReviewScreen, { props: { review } });
	return review;
}

/** Draw a review of the change for a reader who turned stories on in an earlier review. */
async function drawnWithStoriesOn(server: FakeServer, opened: Opened = {}): Promise<Review> {
	return drawn({ settings: await settingsWithStoriesOn(server), ...opened });
}

/** A reader who read the last review they opened as its story: the choice is kept for the next. */
function havingChosenTheStoryLast(): void {
	openReview({ files, story: IN_TWO_CHAPTERS }).views.choose('story');
}

/** The agent tells a story while the page is open: the review says one was told, and the page reads it. */
async function toldMeanwhile(review: Review, server: FakeServer): Promise<void> {
	server.answer('GET /api/story', storyStanding({ held: IN_TWO_CHAPTERS }));
	handOverNext(review, { type: 'story' });
	await settled();
}

describe('a review opened by a reader who read the last one as its story', () => {
	it('opens as its story where they turned stories on', async () => {
		havingChosenTheStoryLast();

		await drawnWithStoriesOn(serving());

		expect(screen.getByTestId('story-view')).toBeTruthy();
	});

	it('opens as its story where one is held, though stories are off', () => {
		havingChosenTheStoryLast();

		drawn({ story: IN_TWO_CHAPTERS });

		expect(screen.getByTestId('story-view')).toBeTruthy();
	});

	it('opens as its story where one is on its way, though this page holds stories as off', () => {
		havingChosenTheStoryLast();

		drawn({ asking: TAKEN });

		expect(screen.getByTestId('story-view')).toBeTruthy();
	});

	it('opens by its files where stories are off and no story is held: nothing was asked for', () => {
		havingChosenTheStoryLast();

		drawn();

		expect(screen.getByTestId('diff-view')).toBeTruthy();
	});
});

describe('Story pressed in the header', () => {
	it('asks before stories are turned on, and leaves the files on screen', async () => {
		const server = serving();
		const user = userEvent.setup();
		drawn();

		await user.click(screen.getByTestId('read-as-story'));

		expect(screen.getByTestId('story-opt-in')).toBeTruthy();
		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(server.requests).toEqual([]);
	});

	it('shows the story view where stories are on', async () => {
		const user = userEvent.setup();
		await drawnWithStoriesOn(serving(), { asking: TAKEN });

		await user.click(screen.getByTestId('read-as-story'));

		expect(screen.getByTestId('story-view')).toBeTruthy();
		expect(screen.queryByTestId('story-opt-in')).toBeNull();
	});

	it('shows a story already held without asking, though stories are off: it is paid for', async () => {
		const user = userEvent.setup();
		drawn({ story: IN_TWO_CHAPTERS });

		await user.click(screen.getByTestId('read-as-story'));

		expect(screen.getByTestId('story-view')).toBeTruthy();
		expect(screen.queryByTestId('story-opt-in')).toBeNull();
	});

	it.each([
		{ where: 'an agent is writing it', asking: TAKEN },
		{ where: 'it waits for an agent to attach', asking: ASKED }
	])(
		'shows the wait for a story asked for elsewhere, where $where, though this page holds stories as off',
		async ({ asking }) => {
			const user = userEvent.setup();
			drawn({ asking });

			await user.click(screen.getByTestId('read-as-story'));

			expect(screen.getByTestId('story-waiting')).toBeTruthy();
			expect(screen.queryByTestId('story-opt-in')).toBeNull();
		}
	);

	it('asks first where the story was stopped and stories are off: writing it again spends tokens', async () => {
		const user = userEvent.setup();
		drawn({ asking: STOPPED });

		await user.click(screen.getByTestId('read-as-story'));

		expect(screen.getByTestId('story-opt-in')).toBeTruthy();
		expect(screen.getByTestId('diff-view')).toBeTruthy();
	});
});

describe('what is asked before stories are turned on', () => {
	it('says what a story is, what it spends on this review, and where stories are turned off', async () => {
		const user = userEvent.setup();
		const review = drawn();

		await user.click(screen.getByTestId('read-as-story'));

		const asked = said(screen.getByTestId('story-opt-in'));
		expect(asked).toContain('Turn on stories?');
		expect(asked).toContain(
			'The agent that made the change tells it as a story: a short overview, then chapters with its reason above each piece of code.'
		);
		expect(asked).toContain(
			`It spends the agent's tokens. The agent reads the whole diff again and writes the story: here up to ${formatWeight(review.weight)} to read and a few thousand to write. Bigger changes cost more.`
		);
		expect(asked).toContain(
			'Stories stay on for every review on this machine. Turn them off in Settings, the gear in the header.'
		);
	});

	it('turns stories on for every review, asks the agent for this one and shows where it will be', async () => {
		const server = serving();
		const user = userEvent.setup();
		drawn();
		await user.click(screen.getByTestId('read-as-story'));

		await user.click(screen.getByTestId('turn-on-stories'));
		await settled();

		expect(server.bodiesSentTo('PUT /api/settings')).toEqual([{ stories: true }]);
		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
		expect(screen.getByTestId('story-view')).toBeTruthy();
		expect(screen.queryByTestId('story-opt-in')).toBeNull();
	});

	it('turns nothing on where the reader says not now, and leaves the files on screen', async () => {
		const server = serving();
		const user = userEvent.setup();
		drawn();
		await user.click(screen.getByTestId('read-as-story'));

		await user.click(screen.getByTestId('stories-not-now'));
		await settled();

		expect(server.requests).toEqual([]);
		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(screen.queryByTestId('story-opt-in')).toBeNull();
	});
});

describe('the Story segment while a story is being written', () => {
	it('says so while the files are read', async () => {
		await drawnWithStoriesOn(serving(), { asking: TAKEN });

		expect(said(screen.getByTestId('read-as-story'))).toBe('Story · writing');
	});

	it('says no more than Story once the story view is on screen: the view says the rest', async () => {
		const user = userEvent.setup();
		await drawnWithStoriesOn(serving(), { asking: TAKEN });

		await user.click(screen.getByTestId('read-as-story'));

		expect(said(screen.getByTestId('read-as-story'))).toBe('Story');
	});

	it.each([
		{ where: 'no agent is attached to write it', asking: ASKED },
		{ where: 'the reader stopped it', asking: STOPPED }
	])('says no more than Story where $where', async ({ asking }) => {
		await drawnWithStoriesOn(serving(), { asking });

		expect(said(screen.getByTestId('read-as-story'))).toBe('Story');
	});
});

describe('a story told while the files are read', () => {
	it('is offered under the switch, with how many chapters it has', async () => {
		const server = serving();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });

		await toldMeanwhile(review, server);

		expect(said(screen.getByTestId('story-ready'))).toBe('The story is ready: 2 chapters. Open it');
		expect(screen.getByTestId('story-ready').getAttribute('role')).toBe('status');
	});

	it('leaves the files on screen: when to read it is for the reader to choose', async () => {
		const server = serving();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });

		await toldMeanwhile(review, server);

		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(screen.queryByTestId('story-view')).toBeNull();
	});

	it('marks the Story segment until it is read', async () => {
		const server = serving();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });

		await toldMeanwhile(review, server);

		expect(screen.getByTestId('story-arrived')).toBeTruthy();
	});

	it('is put away by Escape, and the Story segment stays marked: the story is not read yet', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);

		await user.keyboard('{Escape}');

		expect(screen.queryByTestId('story-ready')).toBeNull();
		expect(screen.getByTestId('story-arrived')).toBeTruthy();
	});

	it('is put away by a press elsewhere on the page, and the Story segment stays marked', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);

		await user.click(screen.getByTestId('diff-view'));

		expect(screen.queryByTestId('story-ready')).toBeNull();
		expect(screen.getByTestId('story-arrived')).toBeTruthy();
	});

	it('stays where the reader presses on the note itself', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);

		await user.click(screen.getByTestId('story-ready'));

		expect(screen.getByTestId('story-ready')).toBeTruthy();
	});

	it('stays where Escape is typed in a field: the key belongs to the field', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN, facts: AGENT_ATTACHED });
		await toldMeanwhile(review, server);
		screen.getByTestId('panel-input').focus();

		await user.keyboard('{Escape}');

		expect(screen.getByTestId('story-ready')).toBeTruthy();
	});

	it('leaves no mark on the Story segment once the story is read, its note put away before', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);
		await user.keyboard('{Escape}');

		await user.click(screen.getByTestId('read-as-story'));
		await user.click(screen.getByTestId('read-as-files'));

		expect(screen.queryByTestId('story-arrived')).toBeNull();
	});

	it('is shown where the reader opens it, and is offered no more', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);

		await user.click(screen.getByTestId('open-story'));

		expect(screen.getByTestId('story-view')).toBeTruthy();
		expect(screen.queryByTestId('story-ready')).toBeNull();
		expect(screen.queryByTestId('story-arrived')).toBeNull();
	});

	it('is offered no more once the reader has read it by the switch and come back to the files', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await toldMeanwhile(review, server);

		await user.click(screen.getByTestId('read-as-story'));
		await user.click(screen.getByTestId('read-as-files'));

		expect(screen.queryByTestId('story-ready')).toBeNull();
		expect(screen.queryByTestId('story-arrived')).toBeNull();
	});
});

describe('a story told while the reader waits for it where it will be', () => {
	it('is drawn there, and offered nowhere: the reader is reading it', async () => {
		const server = serving();
		const user = userEvent.setup();
		const review = await drawnWithStoriesOn(server, { asking: TAKEN });
		await user.click(screen.getByTestId('read-as-story'));

		await toldMeanwhile(review, server);

		expect(screen.getAllByTestId('story-chapter')).toHaveLength(2);
		expect(screen.queryByTestId('story-ready')).toBeNull();
	});
});

describe('a review that opens with its story told', () => {
	it('offers nothing under the switch: no story arrived while the page was open', () => {
		drawn({ story: IN_TWO_CHAPTERS });

		expect(screen.queryByTestId('story-ready')).toBeNull();
		expect(screen.queryByTestId('story-arrived')).toBeNull();
	});
});
