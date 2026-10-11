import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffView from '$lib/components/DiffView.svelte';
import { flushSync } from 'svelte';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';
import { KEPT_AS, keepingImages, paste, screenshot } from '../pasted-images';
import type { Review } from '$lib/review/review.svelte';
import { inReview, leavePage, openReview } from '../review';
import { settled } from '../settled';

let review: Review;

/** Lines 1 to 4 of a file, the third one added. */
const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([
			contextLine(1, 1, 'first = 1'),
			contextLine(2, 2, 'second = 2'),
			addedLine(3, 'third = 3'),
			contextLine(3, 4, 'fourth = 4')
		])
	]
});

/** The number of a line, to pick it by. */
function lineNumber(number: number): HTMLElement {
	const gutter = screen
		.getAllByTestId('line-gutter')
		.find((candidate) => candidate.textContent?.trim() === String(number));
	if (!gutter) throw new Error(`Line ${number} is not drawn`);
	return gutter;
}

/** Every comment field on the page, by what is written in it. */
function fieldsSaying(): string[] {
	return screen.queryAllByTestId('comment-input').map((field) => (field as HTMLTextAreaElement).value);
}

/** Open the review again from what this tab kept, as a reload does, and draw it. */
function reload(): void {
	leavePage();
	document.body.innerHTML = '';
	review = openReview({ files: [file] });
	render(DiffView, inReview(review));
}

beforeEach(() => {
	review = openReview({ files: [file] });
});

describe('a comment being written on lines', () => {
	it('is still there, words and all, when its file is folded and opened again', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await user.type(screen.getByTestId('comment-input'), 'half a thought');

		await user.click(screen.getByTestId('collapse-file'));
		await user.click(screen.getByTestId('collapse-file'));

		expect(fieldsSaying()).toEqual(['half a thought']);
	});

	it('is still there when the diff is read in two columns instead', async () => {
		const user = userEvent.setup();
		keepingSettings(fakeServer());
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await user.type(screen.getByTestId('comment-input'), 'half a thought');

		await review.settings.change({ diff_layout: 'split' });

		expect(screen.getByTestId('split-view')).toBeTruthy();
		expect(fieldsSaying()).toEqual(['half a thought']);
	});

	it('stays when other lines are picked, which start a comment of their own', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(1));
		await user.type(screen.getByTestId('comment-input'), 'on the first');

		await user.click(lineNumber(4));

		expect(fieldsSaying()).toEqual(['on the first', '']);
	});

	it('is brought back, not doubled, when its lines are picked again', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(1));
		await user.type(screen.getByTestId('comment-input'), 'on the first');
		await user.click(lineNumber(4));

		await user.click(lineNumber(1));

		expect(fieldsSaying()).toEqual(['on the first', '']);
		expect(document.activeElement).toBe(screen.getAllByTestId('comment-input')[0]);
	});

	it('comes back after a reload, under its lines, without taking the cursor', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await user.type(screen.getByTestId('comment-input'), 'half a thought');

		reload();

		const [field] = screen.getAllByTestId('comment-input');
		expect((field as HTMLTextAreaElement).value).toBe('half a thought');
		expect(field.closest('tr')?.previousElementSibling?.textContent).toContain('second = 2');
		expect(document.activeElement).not.toBe(field);
	});

	it('opens on a line clicked without a press, as assistive technology and voice control click', async () => {
		render(DiffView, inReview(review));

		await fireEvent.click(lineNumber(2), { detail: 0 });

		expect(fieldsSaying()).toEqual(['']);
	});

	it('opens on a line the keyboard presses, Enter or Space', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));

		lineNumber(2).focus();
		await user.keyboard('{Enter}');
		lineNumber(4).focus();
		await user.keyboard(' ');

		expect(fieldsSaying()).toEqual(['', '']);
	});

	it('lets the server drop what was pasted into it when it is put away unsaid', async () => {
		const user = userEvent.setup();
		const server = keepingImages();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await paste(screen.getByTestId('comment-input'), screenshot());
		await screen.findByTestId('attached-image');

		await user.click(screen.getByTestId('cancel-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));

		expect(fieldsSaying()).toEqual([]);
		expect(server.requests.at(-1)).toMatchObject({ method: 'DELETE', path: `/api/images/${KEPT_AS}` });
	});

	it('lets the server drop what was pasted into it before a reload, when it is put away after', async () => {
		const user = userEvent.setup();
		const server = keepingImages();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await paste(screen.getByTestId('comment-input'), screenshot());
		await screen.findByTestId('attached-image');

		reload();
		await user.click(screen.getByTestId('cancel-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));

		expect(server.requests.at(-1)).toMatchObject({ method: 'DELETE', path: `/api/images/${KEPT_AS}` });
	});

	it('keeps what was pasted into it once its words are in the review', async () => {
		const user = userEvent.setup();
		const server = keepingImages();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await paste(screen.getByTestId('comment-input'), screenshot());
		await screen.findByTestId('attached-image');

		await user.click(screen.getByTestId('save-comment'));

		expect(server.requests).toMatchObject([{ method: 'POST', path: '/api/images' }]);
	});

	it('says it opened, and how it went, and says nothing when it is only folded away', async () => {
		const user = userEvent.setup();
		const report = vi.spyOn(review.commentFields, 'report');
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await user.type(screen.getByTestId('comment-input'), 'Fix this');
		await user.click(screen.getByTestId('collapse-file'));
		await user.click(screen.getByTestId('collapse-file'));

		await user.click(screen.getByTestId('save-comment'));

		expect(report.mock.calls.map(([event]) => event)).toEqual([
			{ type: 'opened', kind: 'new' },
			{ type: 'added', kind: 'new' }
		]);
	});
});

describe('a reply or an edit being written in a thread', () => {
	beforeEach(() => {
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'why two' }));
	});

	it('keeps a reply when the thread is folded and opened again', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(screen.getByTestId('open-reply'));
		await user.type(screen.getByTestId('comment-input'), 'my reply');

		const thread = screen.getByTestId('comment-thread');
		await user.click(within(thread).getAllByTestId('fold-comment')[0]);
		await user.click(within(thread).getByTestId('unfold-thread'));

		expect(fieldsSaying()).toEqual(['my reply']);
	});

	it('brings a reply and an edit back after a reload', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(screen.getByTestId('open-reply'));
		await user.type(screen.getByTestId('comment-input'), 'my reply');
		await user.click(screen.getByTestId('edit-comment'));
		await user.type(screen.getAllByTestId('comment-input')[0], ', and three');

		reload();

		// The thread draws its edit in place of what it says; the reply waits under it
		expect(fieldsSaying()).toEqual(['why two, and three']);
		await user.click(screen.getByTestId('save-comment'));
		expect(fieldsSaying()).toEqual(['my reply']);
	});

	it('lets what was pasted into a reply go with the thread when the thread is deleted', async () => {
		const user = userEvent.setup();
		const server = keepingImages();
		render(DiffView, inReview(review));
		await user.click(screen.getByTestId('open-reply'));
		await paste(screen.getByTestId('comment-input'), screenshot());
		await screen.findByTestId('attached-image');

		await user.click(screen.getByTestId('delete-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));

		expect(server.requests.at(-1)).toMatchObject({ method: 'DELETE', path: `/api/images/${KEPT_AS}` });
	});
});

describe('an image on its way when its field is put away', () => {
	it('is let go on the server as it lands', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		const uploads = server.hold('POST /api/images');
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));
		await paste(screen.getByTestId('comment-input'), screenshot());

		await user.click(screen.getByTestId('cancel-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));
		uploads.answer(0, { image_id: KEPT_AS });
		await settled();

		expect(server.requests.at(-1)).toMatchObject({ method: 'DELETE', path: `/api/images/${KEPT_AS}` });
	});
});

describe('a comment with images of its own', () => {
	it('leaves the images it already had when its edit is put away', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'see this', images: ['kept.png'] }));
		const server = fakeServer();
		render(DiffView, inReview(review));
		await user.click(screen.getByTestId('edit-comment'));

		await user.click(screen.getByTestId('cancel-comment'));

		expect(server.requests.filter((request) => request.method === 'DELETE')).toEqual([]);
	});

	it('keeps an image taken off in an edit that is put away, which the comment still shows', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'see this', images: ['kept.png'] }));
		const server = fakeServer();
		render(DiffView, inReview(review));
		await user.click(screen.getByTestId('edit-comment'));

		await user.click(screen.getByTestId('detach-image'));
		await user.click(screen.getByTestId('cancel-comment'));

		expect(review.threads.all[0].images).toEqual(['kept.png']);
		expect(server.requests.filter((request) => request.method === 'DELETE')).toEqual([]);
	});
});

describe('a comment being written on a removed line, when a narrower base is read', () => {
	/** Line 2 replaced, with the text the review's own base removed, or the one round 1 removed. */
	function replacedLine(removed: string) {
		return diffFile({
			path: 'notes/read.txt',
			hunks: [hunk([contextLine(1, 1, 'keep = 1'), removedLine(2, removed), addedLine(2, 'now = 2')])]
		});
	}

	it('waits, undrawn, while that base owns the removed lines, and comes back with the whole review', async () => {
		const user = userEvent.setup();
		const ours = replacedLine('ours = 2');
		review = openReview({ files: [ours] });
		const server = fakeServer();
		render(DiffView, inReview(review));
		await user.click(removedLineNumber(2));
		await user.type(screen.getByTestId('comment-input'), 'why did this go');

		server.answer(
			'GET /api/diff',
			diffResponse({ files: [replacedLine('theirs = 2')], phrase: 'changes since round 1' })
		);
		await review.diff.setBase('round:1');
		flushSync();
		expect(fieldsSaying()).toEqual([]);

		server.answer('GET /api/diff', diffResponse({ files: [ours] }));
		await review.diff.showWholeReview();
		flushSync();
		expect(fieldsSaying()).toEqual(['why did this go']);
	});
});

/** The number a removed line shows, to pick it by. */
function removedLineNumber(number: number): HTMLElement {
	const gutter = screen
		.getAllByRole('button', { name: `Comment on removed line ${number}` })
		.find((candidate) => candidate.textContent?.trim() === String(number));
	if (!gutter) throw new Error(`Removed line ${number} is not drawn`);
	return gutter;
}
