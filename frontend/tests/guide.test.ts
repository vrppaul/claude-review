import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { tick } from 'svelte';
import AgentPanel from '$lib/components/AgentPanel.svelte';
import CommentBox from '$lib/components/CommentBox.svelte';
import CommentThread from '$lib/components/CommentThread.svelte';
import DiffView from '$lib/components/DiffView.svelte';
import FileList from '$lib/components/FileList.svelte';
import Guide from '$lib/components/Guide.svelte';
import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';
import TopBar from '$lib/components/TopBar.svelte';
import NewsIllustration from '$lib/components/NewsIllustration.svelte';
import { RELEASE_NEWS, type ReleaseNews } from '$lib/guide/news';
import { latestNews, unseenNews } from '$lib/guide/news-choice';
import { TOUR_TARGETS, type TourTarget } from '$lib/guide/tour';
import type { GuideState } from '$lib/types';
import { isNewer, readSeenRelease, writeSeenRelease } from '$lib/utils/seen-release';
import { addedLine, diffFile, diffResponse, hunk } from './diff';
import { fakeServer, SERVER_ERROR, type FakeServer, type ReceivedRequest } from './fake-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const HEADER = { submitting: false, error: null, onOpenModal: ignore };
const FILE = diffFile({ path: 'src/routes.py', hunks: [hunk([addedLine(1, 'y = 3')])] });

/** What `/api/guide` keeps for this reader: the release they were last shown. */
class GuideMemory {
	private seen: string | null;
	private stored: boolean;

	constructor(seen: string | null) {
		this.seen = seen;
		this.stored = seen !== null;
	}

	read(): { record: GuideState; stored: boolean } {
		return { record: { seen_release: this.seen }, stored: this.stored };
	}

	write(request: ReceivedRequest): GuideState {
		this.seen = (request.body as GuideState).seen_release;
		this.stored = true;
		return { seen_release: this.seen };
	}
}

/** Open a review served by this release, and let the guide decide what to show the reader. */
async function arriveAt(release: string): Promise<void> {
	review = openReview({ facts: { release } });
	await review.guide.open();
}

/** A server remembering which release this reader was shown, as `/api/guide` does. */
function guideServer(seen: string | null): FakeServer {
	const server = fakeServer();
	const memory = new GuideMemory(seen);
	server.answerWith('GET /api/guide', () => memory.read());
	server.answerWith('PUT /api/guide', (request) => memory.write(request));
	return server;
}

function entry(release: string, also: string[] = []): ReleaseNews {
	return { release, title: `In ${release}`, body: 'Something new.', also };
}

/** A page on which exactly these places are drawn. */
function pageWith(...names: string[]) {
	review.guide.readPageWith((targets) => targets.some((target) => names.includes(target)));
}

function ignore() {}

/** The header of a review an agent is attached to, once its diff has arrived. */
async function drawHeader() {
	fakeServer().answer('GET /api/diff', diffResponse({ files: [FILE] }));
	await review.diff.take();
	review.answerer.setAttached(true);
	render(TopBar, inReview(review, HEADER));
}

/** The header, with the list of bases it can be read against open. */
async function drawBaseList() {
	const server = fakeServer();
	server.answer('GET /api/diff', diffResponse({ files: [FILE] }));
	server.answer('GET /api/versions', { versions: [] });
	await review.diff.take();
	render(TopBar, inReview(review, HEADER));
	await userEvent.click(screen.getByTestId('base-picker'));
}

function drawFileTree() {
	review = openReview({ files: [FILE] });
	render(FileList, inReview(review));
}

function drawDiff() {
	review = openReview({ files: [FILE] });
	render(DiffView, inReview(review));
}

function drawCommentField() {
	render(CommentBox, inReview(review, { kind: 'new', onSave: ignore, onCancel: ignore }));
}

/** A thread whose question is with the agent, not answered yet. */
async function drawAwaitedQuestion() {
	fakeServer().answer('POST /api/ask', null);
	const id = review.threads.add(newComment({ file: FILE.path, body: 'Why 3?' }));
	await review.threads.ask(id);
	render(CommentThread, inReview(review, { comment: review.threads.all[0] }));
}

function drawAnswer() {
	const id = review.threads.add(newComment({ file: FILE.path, body: 'Why 3?' }));
	review.threads.receiveReply(id, 'It was 2 before the retry path', null);
	render(CommentThread, inReview(review, { comment: review.threads.all[0] }));
}

function drawAgentPanel() {
	review.answerer.setAttached(true);
	render(AgentPanel, inReview(review));
}

/** How to draw the part of the review that holds each place the tour points at. */
const DRAWING: Record<TourTarget, () => void | Promise<void>> = {
	'review-base': drawHeader,
	'review-base-list': drawBaseList,
	'file-tree': drawFileTree,
	'line-number': drawDiff,
	'comment-field': drawCommentField,
	'unsent-count': drawHeader,
	'awaited-answer': drawAwaitedQuestion,
	answer: drawAnswer,
	'agent-panel': drawAgentPanel,
	'agent-panel-toggle': drawHeader,
	send: drawHeader
};

describe('which release a reader has seen', () => {
	it('compares releases number by number', () => {
		expect(isNewer('1.10.0', '1.9.3')).toBe(true);
		expect(isNewer('1.5.0', '1.5.0')).toBe(false);
		expect(isNewer('1.4.2', '1.5.0')).toBe(false);
		expect(isNewer('2.0', '1.99.99')).toBe(true);
	});

	it('counts a pre-release or a development build as the release it leads to', () => {
		expect(isNewer('1.5.0rc1', '1.5.0')).toBe(false);
		expect(isNewer('1.4.3.dev0', '1.4.2')).toBe(true);
	});

	it('is kept by the server, for every review on the machine', async () => {
		guideServer(null);

		expect(await readSeenRelease()).toBeNull();
		await writeSeenRelease('1.5.0');
		expect(await readSeenRelease()).toBe('1.5.0');
	});

	it('takes over the cookie an older release kept it in, once', async () => {
		document.cookie = 'claude-review-seen=1.4.2; path=/';
		const server = guideServer(null);

		expect(await readSeenRelease()).toBe('1.4.2');
		expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ seen_release: '1.4.2' }]);
		expect(document.cookie).not.toContain('claude-review-seen');
	});
});

describe('which news a returning reader is shown', () => {
	const entries = [entry('1.3.0'), entry('1.4.0'), entry('1.5.0')];

	it('is only the newest one they have not seen', () => {
		expect(unseenNews(entries, '1.2.0', '1.5.0')?.release).toBe('1.5.0');
	});

	it('is the newest one they skipped, when the serving release has none', () => {
		expect(unseenNews(entries, '1.3.0', '1.4.5')?.release).toBe('1.4.0');
	});

	it('is nothing, when nothing was written since they last looked', () => {
		expect(unseenNews(entries, '1.5.0', '1.5.2')).toBeUndefined();
	});

	it('never runs ahead of the release that is serving', () => {
		expect(latestNews(entries, '1.4.9')?.release).toBe('1.4.0');
	});

	it('is written for releases in order, each once', () => {
		const releases = RELEASE_NEWS.map((news) => news.release);
		expect(new Set(releases).size).toBe(releases.length);
		expect(releases.every((release, index) => index === 0 || isNewer(release, releases[index - 1]))).toBe(true);
	});
});

describe('what the guide shows a reader arriving', () => {
	it('welcomes somebody who has never opened a review', async () => {
		guideServer(null);

		await arriveAt('1.5.0');

		expect(review.guide.card).toBe('welcome');
	});

	it('tells somebody back from an older release what changed', async () => {
		guideServer('1.4.2');

		await arriveAt('1.5.0');

		expect(review.guide.card).toBe('news');
		expect(review.guide.news?.release).toBe('1.5.0');
	});

	it('says nothing about a release with nothing written since, and remembers it', async () => {
		const server = guideServer('1.5.0');

		await arriveAt('1.5.1');

		expect(review.guide.card).toBeNull();
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ seen_release: '1.5.1' }]));
	});

	it('puts the card away for good once it is closed', async () => {
		const server = guideServer(null);
		await arriveAt('1.5.0');

		review.guide.dismiss();

		expect(review.guide.card).toBeNull();
		await vi.waitFor(() => expect(server.bodiesSentTo('PUT /api/guide')).toEqual([{ seen_release: '1.5.0' }]));
	});

	it('shows nothing rather than welcome somebody twice when the server cannot say', async () => {
		fakeServer().refuse('GET /api/guide', SERVER_ERROR);

		await arriveAt('1.5.0');

		expect(review.guide.card).toBeNull();
	});
});

describe('the news card', () => {
	it('links to the release on GitHub even when there is nothing else to list', async () => {
		guideServer('1.4.2');
		await arriveAt('1.5.0');

		const { getByTestId } = render(Guide, inReview(review));
		await tick();

		expect(getByTestId('guide-release-link').getAttribute('href')).toBe(
			'https://github.com/vrppaul/claude-review/releases/tag/v1.5.0'
		);
	});

	it('shows a picture from a file, described for whoever cannot see it', () => {
		const { getByTestId } = render(
			NewsIllustration,
			inReview(review, { illustration: { kind: 'image', src: '/news/paste.gif', alt: 'A screenshot pasted' } })
		);

		const image = getByTestId('news-image') as HTMLImageElement;
		expect(image.getAttribute('src')).toBe('/news/paste.gif');
		expect(image.alt).toBe('A screenshot pasted');
	});
});

describe('every place the tour points at', () => {
	it.each(TOUR_TARGETS)('is drawn by the review: %s', async (target) => {
		await DRAWING[target]();

		expect(document.querySelector(`[data-tour="${target}"]`)).not.toBeNull();
	});
});

describe('the tour', () => {
	beforeEach(() => {
		guideServer(null);
	});

	it('takes the steps a review with an agent has, and leaves out the others', () => {
		review.answerer.setAttached(true);
		review.guide.startTour();
		const seen: string[] = [];
		while (review.guide.step) {
			seen.push(review.guide.step.id);
			review.guide.next();
		}

		expect(seen).toContain('comment-route');
		expect(seen).toContain('round-or-end');
		expect(seen).not.toContain('comment-save');
		expect(seen).not.toContain('finish');
	});

	it('stays on the same part of the tour when an agent joins in the middle of it', () => {
		review.guide.startTour();
		while (review.guide.step && review.guide.step.id !== 'comment-save') review.guide.next();
		expect(review.guide.step?.id).toBe('comment-save');

		review.answerer.setAttached(true);

		// With an agent there, saving a comment is one of the ways it can go
		expect(review.guide.step?.id).toBe('comment-route');
	});

	it('stays at the end of the tour when an agent joins on its last step', () => {
		review.guide.startTour();
		while (review.guide.step && review.guide.step.id !== 'finish') review.guide.next();
		expect(review.guide.step?.id).toBe('finish');

		review.answerer.setAttached(true);

		expect(review.guide.step?.id).toBe('round-or-end');
		expect(review.guide.isLastStep).toBe(true);
	});

	it('passes over a step with nothing on screen to show', () => {
		// A plan under review has no base to choose: the tour opens on the files
		pageWith('file-tree', 'line-number');

		review.guide.startTour();

		expect(review.guide.step?.id).toBe('files');
	});

	it('turns round at the start rather than landing on a step with nothing to show', () => {
		pageWith('file-tree', 'line-number');
		review.guide.startTour();

		review.guide.back();

		expect(review.guide.step?.id).toBe('files');
	});

	it('waits for a comment on a line, not for a reply', () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.startTour();
		review.guide.next();
		expect(review.guide.step?.id).toBe('comment-line');

		review.guide.notice({ type: 'opened', kind: 'reply' });
		expect(review.guide.step?.id).toBe('comment-line');

		review.guide.notice({ type: 'opened', kind: 'new' });
		expect(review.guide.step?.id).toBe('comment-save');
	});

	it('does not wait for a comment that is already open', () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.notice({ type: 'opened', kind: 'new' });

		review.guide.startTour();
		review.guide.next();

		expect(review.guide.step?.id).toBe('comment-save');
	});

	it('follows the comment where the reader sent it', () => {
		review.answerer.setAttached(true);
		pageWith('file-tree', 'line-number', 'comment-field', 'awaited-answer', 'unsent-count');
		review.guide.startTour();
		review.guide.next();
		review.guide.notice({ type: 'opened', kind: 'new' });
		expect(review.guide.step?.id).toBe('comment-route');

		review.guide.notice({ type: 'asked', kind: 'new' });

		expect(review.guide.step?.id).toBe('asked');
	});

	it('goes back a step when the comment is closed without being sent', () => {
		review.answerer.setAttached(true);
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.startTour();
		review.guide.next();
		review.guide.notice({ type: 'opened', kind: 'new' });

		review.guide.notice({ type: 'closed', kind: 'new' });

		expect(review.guide.step?.id).toBe('comment-line');
	});

	it('leaves Escape to whatever is open over the review', async () => {
		pageWith('review-base');
		review.guide.startTour();
		render(Guide, inReview(review));
		await tick();

		window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

		expect(review.guide.touring).toBe(true);
	});

	it('keeps waiting for a comment while another one on a line is still open', () => {
		review.answerer.setAttached(true);
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.startTour();
		review.guide.next();
		review.guide.notice({ type: 'opened', kind: 'new' });
		review.guide.notice({ type: 'opened', kind: 'new' });

		review.guide.notice({ type: 'closed', kind: 'new' });

		expect(review.guide.step?.id).toBe('comment-route');
	});

	it('counts only the steps it will show, and offers no Back before the first', () => {
		pageWith('file-tree', 'line-number');
		review.guide.startTour();

		expect(review.guide.stepPosition).toBe(0);
		expect(review.guide.canGoBack).toBe(false);
		expect(review.guide.stepCount).toBe(2);
	});

	it('hears the comment fields once the page shows what happened', async () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.startTour();
		render(Guide, inReview(review));
		await tick();
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.next();

		review.commentFields.report({ type: 'opened', kind: 'new' });
		expect(review.guide.step?.id).toBe('comment-line');
		await tick();

		expect(review.guide.step?.id).toBe('comment-save');
	});
});

describe('the ? list', () => {
	it('opens from a button too, for whoever has ? taken by a browser extension', async () => {
		const { getByTestId, queryByTestId } = render(KeyboardShortcuts, inReview(review));
		const { getByTestId: inHeader } = render(TopBar, inReview(review, HEADER));
		expect(queryByTestId('shortcuts-list')).toBeNull();

		inHeader('open-help').click();
		await tick();

		expect(getByTestId('shortcuts-list')).toBeTruthy();
	});
});
