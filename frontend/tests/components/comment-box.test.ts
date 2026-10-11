import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentBox from '$lib/components/CommentBox.svelte';
import { KEPT_AS, keepingImages, paste, screenshot } from '../pasted-images';
import { newComment } from '../new-comment';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { NewComment } from '$lib/types';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/** A comment being started on line 5 of a file, as picking the line starts one. */
function newField(): CommentField {
	const line = { side: 'new', number: 5 } as const;
	review.threads.writing.pickLines('a.ts', { side: 'new', startLine: 5, endLine: 5, opensBelow: line }, ['x = 5']);
	return review.threads.writing.onLinesOf('a.ts')[0];
}

/** A field drawn as the page draws it, its words going into the review when saved. */
function drawnSaving(field: CommentField, label = 'Line 5') {
	return render(
		CommentBox,
		inReview(review, { field, onSave: () => review.threads.say(field), onCancel: vi.fn(), label })
	);
}

/** What the comment saved says, as the review holds it. */
function saved() {
	const [thread] = review.threads.all;
	if (!thread) throw new Error('Nothing was saved');
	return thread;
}

/** The edit of a comment already written, as its Edit button opens one. */
function editOf(written: Partial<NewComment>): CommentField {
	const id = review.threads.add({ ...newComment(), ...written });
	const thread = review.threads.all.find((candidate) => candidate.id === id);
	if (!thread) throw new Error('The comment was not written');
	review.threads.writing.openEdit(thread);
	const field = review.threads.writing.edit(id);
	if (!field) throw new Error('No edit was opened');
	return field;
}

describe('a comment field', () => {
	it('saves what was written, without the spaces around it', async () => {
		const { getByTestId } = drawnSaving(newField());

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		await userEvent.type(input, '  Fix this  ');
		await userEvent.click(getByTestId('save-comment'));

		expect(saved().body).toBe('Fix this');
	});

	it('cannot save an empty comment', () => {
		const { getByTestId } = render(
			CommentBox,
			inReview(review, { field: newField(), onSave: vi.fn(), onCancel: vi.fn() })
		);

		expect((getByTestId('save-comment') as HTMLButtonElement).disabled).toBe(true);
	});

	it('closes when the reader cancels', async () => {
		const onCancel = vi.fn();
		const { getByTestId } = render(CommentBox, inReview(review, { field: newField(), onSave: vi.fn(), onCancel }));

		await userEvent.click(getByTestId('cancel-comment'));

		expect(onCancel).toHaveBeenCalled();
	});

	it('says where the comment hangs', () => {
		const { getByText } = render(
			CommentBox,
			inReview(review, { field: newField(), onSave: vi.fn(), onCancel: vi.fn(), label: 'Lines 10-15' })
		);

		expect(getByText('Lines 10-15')).toBeTruthy();
	});

	it('reopens with what the comment already says', () => {
		const { getByTestId } = render(
			CommentBox,
			inReview(review, { field: editOf({ body: 'existing text' }), onSave: vi.fn(), onCancel: vi.fn() })
		);

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		expect(input.value).toBe('existing text');
	});
});

describe('suggesting a replacement', () => {
	it('starts the suggestion from the lines being commented on', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(
			CommentBox,
			inReview(review, {
				field: newField(),
				onSave: vi.fn(),
				onCancel: vi.fn(),
				label: 'Lines 3',
				suggestFrom: ['    if x:', '        return 1']
			})
		);

		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('```suggestion\n    if x:\n        return 1\n```');
	});

	it('keeps what was already written above the suggestion', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(
			CommentBox,
			inReview(review, {
				field: newField(),
				onSave: vi.fn(),
				onCancel: vi.fn(),
				label: 'Line 3',
				suggestFrom: ['x = 1']
			})
		);

		await user.type(getByTestId('comment-input'), 'Name it after the unit');
		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('Name it after the unit\n\n```suggestion\nx = 1\n```');
	});

	it('offers nothing to suggest when no lines were given', () => {
		const { queryByTestId } = render(
			CommentBox,
			inReview(review, { field: newField(), onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 3' })
		);

		expect(queryByTestId('suggest-change')).toBeNull();
	});

	it('will not start a second suggestion in one comment', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(
			CommentBox,
			inReview(review, {
				field: newField(),
				onSave: vi.fn(),
				onCancel: vi.fn(),
				label: 'Line 3',
				suggestFrom: ['x = 1']
			})
		);

		await user.click(getByTestId('suggest-change'));

		expect((getByTestId('suggest-change') as HTMLButtonElement).disabled).toBe(true);
	});
});

describe('how a comment is meant', () => {
	it('is an ordinary note unless said otherwise', async () => {
		const user = userEvent.setup();
		const { getByTestId } = drawnSaving(newField());

		await user.type(getByTestId('comment-input'), 'Reads well');
		await user.click(getByTestId('save-comment'));

		expect(saved()).toMatchObject({ body: 'Reads well', severity: 'note' });
	});

	it('can be marked as a question', async () => {
		const user = userEvent.setup();
		const { getByTestId } = drawnSaving(newField());

		await user.click(getByTestId('severity-question'));
		await user.type(getByTestId('comment-input'), 'Is this reachable?');
		await user.click(getByTestId('save-comment'));

		expect(saved()).toMatchObject({ body: 'Is this reachable?', severity: 'question' });
	});

	it('reopens for editing with the mark it was saved under', async () => {
		const { getByTestId } = render(
			CommentBox,
			inReview(review, { field: editOf({ severity: 'blocker' }), onSave: vi.fn(), onCancel: vi.fn(), label: 'Line 1' })
		);

		expect(getByTestId('severity-blocker').getAttribute('aria-pressed')).toBe('true');
	});
});

describe('images in a comment', () => {
	it('saves a pasted screenshot as the whole comment', async () => {
		keepingImages();
		const { getByTestId, findByTestId } = drawnSaving(newField());

		await paste(getByTestId('comment-input'), screenshot());
		await findByTestId('attached-image');
		await userEvent.click(getByTestId('save-comment'));

		expect(saved()).toMatchObject({ body: '', images: [KEPT_AS] });
	});
});

describe('a comment field, to whoever cannot see it', () => {
	it('is named by the lines it hangs on', () => {
		const { getByLabelText, getByTestId } = drawnSaving(newField());

		expect(getByLabelText('Line 5')).toBe(getByTestId('comment-input'));
	});

	it('is a reply where it hangs on nothing of its own', () => {
		const field = newField();
		const { getByLabelText, getByTestId } = render(
			CommentBox,
			inReview(review, { field, onSave: vi.fn(), onCancel: vi.fn(), severityPicker: false, nested: true })
		);

		expect(getByLabelText('Reply')).toBe(getByTestId('comment-input'));
	});
});
