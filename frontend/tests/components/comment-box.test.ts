import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentBox from '$lib/components/CommentBox.svelte';
import { tick } from 'svelte';
import { KEPT_AS, keepingImages, paste, screenshot } from '../pasted-images';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

describe('a comment field', () => {
	it('saves what was written, without the spaces around it', async () => {
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave, onCancel: vi.fn(), label: 'Line 5' }));

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		await userEvent.type(input, '  Fix this  ');
		await userEvent.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Fix this', 'note', []);
	});

	it('cannot save an empty comment', () => {
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn() }));

		expect((getByTestId('save-comment') as HTMLButtonElement).disabled).toBe(true);
	});

	it('closes when the reader cancels', async () => {
		const onCancel = vi.fn();
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel }));

		await userEvent.click(getByTestId('cancel-comment'));

		expect(onCancel).toHaveBeenCalled();
	});

	it('says where the comment hangs', () => {
		const { getByText } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Lines 10-15' }));

		expect(getByText('Lines 10-15')).toBeTruthy();
	});

	it('reopens with what the comment already says', () => {
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), initialBody: 'existing text' }));

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		expect(input.value).toBe('existing text');
	});
});

describe('suggesting a replacement', () => {
	it('starts the suggestion from the lines being commented on', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, inReview(review, {
				kind: 'new',
				onSave: vi.fn(),
				onCancel: vi.fn(),
				label: 'Lines 3',
				suggestFrom: ['    if x:', '        return 1']
			}));

		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('```suggestion\n    if x:\n        return 1\n```');
	});

	it('keeps what was already written above the suggestion', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, inReview(review, {
				kind: 'new',
				onSave: vi.fn(),
				onCancel: vi.fn(),
				label: 'Line 3',
				suggestFrom: ['x = 1']
			}));

		await user.type(getByTestId('comment-input'), 'Name it after the unit');
		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('Name it after the unit\n\n```suggestion\nx = 1\n```');
	});

	it('offers nothing to suggest when no lines were given', () => {
		const { queryByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 3' }));

		expect(queryByTestId('suggest-change')).toBeNull();
	});

	it('will not start a second suggestion in one comment', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 3', suggestFrom: ['x = 1'] }));

		await user.click(getByTestId('suggest-change'));

		expect((getByTestId('suggest-change') as HTMLButtonElement).disabled).toBe(true);
	});
});

describe('how a comment is meant', () => {
	it('is an ordinary note unless said otherwise', async () => {
		const user = userEvent.setup();
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave, onCancel: vi.fn(), label: 'Line 1' }));

		await user.type(getByTestId('comment-input'), 'Reads well');
		await user.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Reads well', 'note', []);
	});

	it('can be marked as a question', async () => {
		const user = userEvent.setup();
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave, onCancel: vi.fn(), label: 'Line 1' }));

		await user.click(getByTestId('severity-question'));
		await user.type(getByTestId('comment-input'), 'Is this reachable?');
		await user.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Is this reachable?', 'question', []);
	});

	it('reopens for editing with the mark it was saved under', async () => {
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 1', initialSeverity: 'blocker' }));

		expect(getByTestId('severity-blocker').getAttribute('aria-pressed')).toBe('true');
	});
});

describe('images in a comment', () => {
	beforeEach(() => {
	});

	it('saves a pasted screenshot as the whole comment', async () => {
		keepingImages();
		const onSave = vi.fn();
		const { getByTestId, findByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave, onCancel: vi.fn(), label: 'Line 5' }));

		await paste(getByTestId('comment-input'), screenshot());
		await findByTestId('attached-image');
		await userEvent.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('', 'note', [KEPT_AS]);
	});

	it('lets the server drop what was pasted when the field closes unsent', async () => {
		// Cancel, a click on another line, a folded thread: each closes the field
		const server = keepingImages();
		const { getByTestId, findByTestId, unmount } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 5' }));

		await paste(getByTestId('comment-input'), screenshot());
		await findByTestId('attached-image');
		unmount();

		expect(server.requests.at(-1)).toMatchObject({
			method: 'DELETE',
			path: `/api/images/${KEPT_AS}`
		});
	});

	it('keeps what was pasted once the comment is saved', async () => {
		const server = keepingImages();
		const { getByTestId, findByTestId, unmount } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 5' }));

		await paste(getByTestId('comment-input'), screenshot());
		await findByTestId('attached-image');
		await userEvent.click(getByTestId('save-comment'));
		unmount();

		expect(server.requests).toMatchObject([{ method: 'POST', path: '/api/images' }]);
	});

	it('leaves the images a comment already had when an edit closes unsent', async () => {
		const server = keepingImages();
		const { unmount } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), initialBody: 'This', initialImages: ['kept.png'] }));

		unmount();

		expect(server.requests).toEqual([]);
	});
});

describe('what a comment field says happened to it', () => {
	it('says it opened, and what became of it, naming which kind of field it is', async () => {
		const report = vi.spyOn(review.commentFields, 'report');
		const { getByTestId } = render(CommentBox, inReview(review, { kind: 'new', onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 5' }));

		await userEvent.type(getByTestId('comment-input'), 'Fix this');
		await userEvent.click(getByTestId('save-comment'));

		expect(report.mock.calls.map(([event]) => event)).toEqual([
			{ type: 'opened', kind: 'new' },
			{ type: 'added', kind: 'new' }
		]);
	});

	it('says it closed when it goes without being sent', async () => {
		const report = vi.spyOn(review.commentFields, 'report');
		const { unmount } = render(CommentBox, inReview(review, { kind: 'reply', onSave: vi.fn(), onCancel: vi.fn() }));
		await tick();

		unmount();
		await tick();

		expect(report).toHaveBeenLastCalledWith({ type: 'closed', kind: 'reply' });
	});
});
