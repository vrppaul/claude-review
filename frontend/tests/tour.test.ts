import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync, tick } from 'svelte';
import AgentPanel from '$lib/components/AgentPanel.svelte';
import CommentBox from '$lib/components/CommentBox.svelte';
import CommentThread from '$lib/components/CommentThread.svelte';
import DiffView from '$lib/components/DiffView.svelte';
import FileList from '$lib/components/FileList.svelte';
import Guide from '$lib/components/Guide.svelte';
import GuideCard from '$lib/components/GuideCard.svelte';
import TopBar from '$lib/components/TopBar.svelte';
import { TOUR_TARGETS, type TourTarget } from '$lib/guide/tour';
import { addedLine, diffFile, diffResponse, hunk } from './diff';
import { fakeServer } from './fake-server';
import { guideServer } from './guide-server';
import { newComment } from './new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from './review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

const HEADER = { submitting: false, error: null, onOpenModal: ignore };
const FILE = diffFile({ path: 'src/routes.py', hunks: [hunk([addedLine(1, 'y = 3')])] });

// How the tour says how far along it is: "2 of 7"
const STEP_COUNT = /^\d+ of \d+$/;

/** A page on which exactly these places are drawn. */
function pageWith(...names: TourTarget[]) {
	review.guide.seeTargets(new Set(names));
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
	const line = { side: 'new', number: 1 } as const;
	review.threads.writing.pickLines(FILE.path, { side: 'new', startLine: 1, endLine: 1, opensBelow: line });
	const [field] = review.threads.writing.onLinesOf(FILE.path);
	render(CommentBox, inReview(review, { field, onSave: ignore, onCancel: ignore }));
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

	it('counts again the moment a comment field opens, which a step was waiting for', () => {
		pageWith('file-tree', 'line-number', 'comment-field');
		review.guide.startTour();
		const { getByText } = render(GuideCard, inReview(review));
		const before = getByText(STEP_COUNT).textContent;

		review.guide.notice({ type: 'opened', kind: 'new' });
		flushSync();

		expect(getByText(STEP_COUNT).textContent).not.toBe(before);
	});

	it('counts only the steps it will show, and offers no Back before the first', () => {
		pageWith('file-tree', 'line-number');
		review.guide.startTour();

		expect(review.guide.stepPosition).toBe(0);
		expect(review.guide.canGoBack).toBe(false);
		expect(review.guide.stepCount).toBe(2);
	});

	it('moves on from a step it landed on before the page said what it has drawn', () => {
		review.guide.startTour();
		const landedOn = review.guide.step?.id;

		pageWith('file-tree', 'line-number');

		expect(landedOn).toBe('review-base');
		expect(review.guide.step?.id).toBe('files');
	});

	it('asks the page afresh what it has drawn when the tour is taken again', () => {
		pageWith('file-tree', 'line-number');
		review.guide.startTour();
		review.guide.endTour();

		review.guide.startTour();

		expect(review.guide.step?.id).toBe('review-base');
	});

	it('asks the page afresh what it has drawn when the tour is taken again after its last step', () => {
		pageWith('file-tree', 'line-number');
		review.guide.startTour();
		while (review.guide.touring) review.guide.next();

		review.guide.startTour();

		expect(review.guide.step?.id).toBe('review-base');
	});

	it('looks over the page only while the tour runs', async () => {
		const seen = vi.spyOn(review.guide, 'seeTargets');
		render(Guide, inReview(review));
		await tick();
		expect(seen).not.toHaveBeenCalled();

		review.guide.startTour();
		await tick();

		expect(seen).toHaveBeenCalled();
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
