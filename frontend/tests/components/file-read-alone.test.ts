import { beforeEach, describe, it, expect } from 'vitest';
import { flushSync } from 'svelte';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { Anchor, DiffFile, FileOfTakeResponse } from '$lib/types';
import { A_LATER_TAKE, addedLine, contextLine, diffFile, diffResponse, hunk } from '../diff';
import { type FakeServer, fakeServer } from '../fake-server';
import { frames } from '../frames';
import { newComment, onAFileGone } from '../new-comment';
import { openReview } from '../review';
import { settled } from '../settled';
import { storyResponse } from '../story';

// The change touches a.py; src/caller.py, which calls into it, the change left as it was
const A_PY = diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'in a.py')])] });
const CALLER = 'src/caller.py';
const CALLER_OF_THE_TAKE: FileOfTakeResponse = {
	path: CALLER,
	hunk: hunk(
		[contextLine(null, 1, 'def caller():'), contextLine(null, 2, '    handler()'), contextLine(null, 3, '    return')],
		{ header: '' }
	),
	commentable: true
};
// What the server says of a file of the take it could not read
const SERVER_FAILED = 500;

let review: Review;
let server: FakeServer;

beforeEach(() => {
	server = fakeServer();
	server.answer('GET /api/file-of-take', CALLER_OF_THE_TAKE);
});

/** Open the review of a change to these files, on screen. */
function openedOn(files: DiffFile[]): void {
	review = openReview({ files });
	render(ReviewScreen, { props: { review } });
}

/** Let the page read what it asked for and take the reader where it goes, until they come to rest. */
async function cameToRest(): Promise<void> {
	await settled();
	await frames();
}

/** Press a control by its test id, and let the page come to rest. */
async function press(testId: string): Promise<void> {
	await userEvent.setup({ delay: null }).click(screen.getByTestId(testId));
	await cameToRest();
}

/** Raise a thread on the file the change did not touch, as the agent does, and take the reader to it. */
async function goneToAThreadOnTheCaller(): Promise<void> {
	review.threads.add(newComment({ file: CALLER, startLine: 2, body: 'the agent forgot this call' }));
	const [thread] = review.threads.all;
	review.navigator.reveal(thread);
	await cameToRest();
}

describe('a file the change did not touch, read alone', () => {
	beforeEach(() => {
		openedOn([A_PY]);
	});

	it('is where a thread on it takes the reader: whole, in place of the change, the keyboard on the thread', async () => {
		await goneToAThreadOnTheCaller();

		const alone = screen.getByTestId('file-alone-view');
		expect(within(alone).getByTestId('file-alone-heading').textContent).toBe(CALLER);
		expect(within(alone).getByTestId('file-alone-header').textContent).toContain('not in this change');
		expect(within(alone).getByTestId('file-lines').textContent).toContain('def caller():');
		expect(within(alone).getByTestId('file-lines').textContent).toContain('return');
		expect(screen.queryByTestId('diff-view')).toBeNull();
		expect(document.activeElement?.textContent).toContain('the agent forgot this call');
	});

	it('takes a comment on its line, as any line does', async () => {
		const user = userEvent.setup();
		await goneToAThreadOnTheCaller();

		await user.click(screen.getByRole('button', { name: 'Comment on line 3' }));
		await user.type(screen.getByTestId('comment-input'), 'handle the lock here too');
		await user.click(screen.getByTestId('save-comment'));

		expect(review.threads.all.map((thread) => thread.anchor)).toContainEqual(
			expect.objectContaining({ file: CALLER, side: 'new', start_line: 3 })
		);
	});

	it('notes where the reader came into it from, and is put away back there, leaving no way back', async () => {
		await goneToAThreadOnTheCaller();
		expect(screen.getByTestId('go-back').textContent?.trim()).toBe('Back to a.py:1');

		await press('put-file-away');

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('1');
		expect(screen.queryByTestId('go-back')).toBeNull();
	});

	it('shows Files chosen in the header while it is read, and leaves for the change’s files by it', async () => {
		await goneToAThreadOnTheCaller();
		expect(screen.getByTestId('read-as-files').getAttribute('aria-pressed')).toBe('true');

		await press('read-as-files');

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(screen.getByTestId('diff-view').textContent).toContain('in a.py');
	});

	it('is walked into by n from the change’s threads, and out of again to the first of them', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'on the change' }));
		review.threads.add(newComment({ file: CALLER, startLine: 2, body: 'on the caller' }));
		flushSync();

		await user.keyboard('n');
		await cameToRest();
		await user.keyboard('n');
		await cameToRest();
		const second = document.activeElement?.textContent;
		await user.keyboard('n');
		await cameToRest();

		expect(second).toContain('on the caller');
		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(document.activeElement?.textContent).toContain('on the change');
	});

	it('says why it could not be read under its bar, and reads it again at Try again', async () => {
		server.refuse('GET /api/file-of-take', SERVER_FAILED, 'the repository could not be read');
		await goneToAThreadOnTheCaller();
		expect(screen.getByTestId('file-alone-failed').textContent).toBe('the repository could not be read');

		server.answer('GET /api/file-of-take', CALLER_OF_THE_TAKE);
		await press('read-file-again');

		expect(screen.queryByTestId('file-alone-failed')).toBeNull();
		expect(screen.getByTestId('file-lines').textContent).toContain('def caller():');
	});
});

describe('a file read alone, come to from nowhere', () => {
	it('is put away to the change’s files, with no way back offered', async () => {
		// A change of no file: there is no line to read, and so no place left as the reader is taken in
		openedOn([]);
		await goneToAThreadOnTheCaller();
		expect(screen.queryByTestId('go-back')).toBeNull();

		await press('put-file-away');

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(screen.getByTestId('no-changes').textContent?.trim()).toBe('No changes found.');
	});
});

describe('a file read alone, as the change is taken again', () => {
	// What the server says of a file the take holds none of
	const NO_SUCH_FILE = 404;

	/** Take the change again, as a round landing does: the threads followed to these anchors, the diff these files. */
	async function retakenWith(files: DiffFile[], anchors: Anchor[]): Promise<void> {
		server.answer('POST /api/anchors/follow', { anchors });
		server.answer('GET /api/diff', diffResponse({ files, take: A_LATER_TAKE }));
		server.answer('GET /api/story', storyResponse());
		await review.takeRetakenDiff();
		await cameToRest();
	}

	beforeEach(async () => {
		openedOn([A_PY]);
		await goneToAThreadOnTheCaller();
	});

	it('is read anew for the take, as it stands now', async () => {
		server.answer('GET /api/file-of-take', {
			...CALLER_OF_THE_TAKE,
			hunk: hunk([contextLine(null, 1, 'def caller_renamed():')], { header: '' })
		});

		await retakenWith([A_PY], [review.threads.all[0].anchor]);

		expect(screen.getByTestId('file-lines').textContent).toContain('def caller_renamed():');
	});

	it('gives way to the change’s files once the change touches it', async () => {
		const callerChanged = diffFile({ path: CALLER, hunks: [hunk([addedLine(1, 'import lock')])] });

		await retakenWith([A_PY, callerChanged], [review.threads.all[0].anchor]);

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(screen.getAllByTestId('file-section').map((section) => section.dataset.path)).toEqual(['a.py', CALLER]);
	});

	it('says in place that the take holds it no more, and its thread is drawn above the change’s files', async () => {
		server.refuse('GET /api/file-of-take', NO_SUCH_FILE, `no file of the take on screen at ${CALLER}`);

		await retakenWith([A_PY], [{ ...review.threads.all[0].anchor, standing: 'file_gone' }]);
		expect(screen.getByTestId('file-alone-failed').textContent).toBe(`no file of the take on screen at ${CALLER}`);
		await press('put-file-away');

		expect(screen.getByTestId('unplaced-threads').textContent).toContain('the agent forgot this call');
	});
});

describe('the tree, beside the change’s files and a file read alone', () => {
	beforeEach(() => {
		openedOn([A_PY]);
	});

	/** The rows the tree lists under "Not in this change", by what each says. */
	function listedOutside(): string[] {
		return screen.queryAllByTestId('outside-file').map((row) => row.textContent?.replace(/\s+/g, ' ').trim());
	}

	it('lists each file a thread is read alone in, with its threads, and none whose file is gone', () => {
		review.threads.add(newComment({ file: CALLER, startLine: 2, body: 'the agent forgot this call' }));
		review.threads.add(onAFileGone({ file: 'gone.py', body: 'on a file removed again' }));
		flushSync();

		expect(within(screen.getByTestId('sidebar')).getByText('Not in this change')).toBeTruthy();
		expect(listedOutside()).toEqual(['caller.py 1 src/']);
	});

	it('opens a file it lists alone at a press on its row, the row the current one', async () => {
		review.threads.add(newComment({ file: CALLER, startLine: 2, body: 'the agent forgot this call' }));
		flushSync();

		await press('outside-file');

		expect(screen.getByTestId('file-alone-heading').textContent).toBe(CALLER);
		expect(screen.getByTestId('outside-file').getAttribute('aria-current')).toBe('true');
	});

	it('keeps a file put away listed while a thread is read in it', async () => {
		await goneToAThreadOnTheCaller();

		await press('put-file-away');

		expect(listedOutside()).toEqual(['caller.py 1 src/']);
	});

	it('lists a file put away no more where nothing of the reader’s hangs on it', async () => {
		review.threads.add(newComment({ file: CALLER, startLine: 2, body: 'the agent forgot this call' }));
		flushSync();
		await press('outside-file');
		review.threads.remove(review.threads.all[0].id);
		await cameToRest();
		expect(listedOutside()).toEqual(['caller.py src/']);

		await press('put-file-away');

		expect(listedOutside()).toEqual([]);
	});

	it('keeps a file put away listed while a comment is being written on its line', async () => {
		const user = userEvent.setup();
		await goneToAThreadOnTheCaller();
		await user.click(screen.getByRole('button', { name: 'Comment on line 3' }));
		await user.type(screen.getByTestId('comment-input'), 'not sent yet');
		review.threads.remove(review.threads.all[0].id);
		await cameToRest();

		await press('put-file-away');

		expect(listedOutside()).toEqual(['caller.py src/']);
	});

	it('leaves the file read alone for the change’s files at a press on a file of the change', async () => {
		await goneToAThreadOnTheCaller();

		await press('file-item');

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(screen.getByTestId('diff-view').textContent).toContain('in a.py');
	});
});
