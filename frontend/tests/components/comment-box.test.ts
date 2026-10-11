import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentBox from '$lib/components/CommentBox.svelte';
import { FIELD_KEYS } from '$lib/components/keymap';
import { KEPT_AS, keepingImages, paste, screenshot, SEND_LIMITS } from '../pasted-images';
import { newComment } from '../new-comment';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { NewComment } from '$lib/types';
import type { Review } from '$lib/review/review.svelte';
import { inReview, leavePage, openReview } from '../review';

let review: Review;

// The longest text a test's server takes, short enough to type past
const SHORTEST = 5;

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
	it('takes no more text than the server takes', async () => {
		review = openReview({ facts: { limits: { ...SEND_LIMITS, max_text_length: SHORTEST } } });
		const { getByTestId } = drawnSaving(newField());

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		await userEvent.type(input, 'Longer than that');

		expect(input.value).toBe('Longe');
	});

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

describe('the chord a field answers', () => {
	it('adds the comment on the chord the help lists, and says so beside it', async () => {
		const user = userEvent.setup();
		const { getByTestId, getByText } = drawnSaving(newField());

		await user.type(getByTestId('comment-input'), 'Fix this');
		await user.keyboard('{Control>}{Enter}{/Control}');

		expect(saved().body).toBe('Fix this');
		expect(getByText((said) => said.includes(FIELD_KEYS))).toBeTruthy();
	});

	it('leaves the chord with Shift to the review, which it finishes', async () => {
		const user = userEvent.setup();
		const { getByTestId } = drawnSaving(newField());

		await user.type(getByTestId('comment-input'), 'Fix this');
		await user.keyboard('{Control>}{Shift>}{Enter}{/Shift}{/Control}');

		expect(review.threads.count).toBe(0);
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

	it('asks for a reply in the words that opened it, and for a comment in its own', () => {
		const id = review.threads.add(newComment({ body: 'Why?' }));
		review.threads.writing.openReply(id);
		const reply = review.threads.writing.reply(id);
		if (!reply) throw new Error('No reply was opened');

		const replying = render(
			CommentBox,
			inReview(review, { field: reply, onSave: vi.fn(), onCancel: vi.fn(), severityPicker: false, nested: true })
		);
		expect(replying.getByTestId('comment-input').getAttribute('placeholder')).toBe('Write a reply…');
		replying.unmount();

		const commenting = drawnSaving(newField());
		expect(commenting.getByTestId('comment-input').getAttribute('placeholder')).toBe('What should change here?');
	});
});

describe('putting a comment away', () => {
	/** A field drawn as the page draws it, with what putting it away does recorded. */
	function drawnPuttingAway(field: CommentField) {
		const onCancel = vi.fn();
		const drawn = render(CommentBox, inReview(review, { field, onSave: vi.fn(), onCancel, label: 'Line 5' }));
		return { ...drawn, onCancel };
	}

	it('asks before Escape drops the words written in it, and drops them only on yes', async () => {
		const user = userEvent.setup();
		const { getByTestId, onCancel } = drawnPuttingAway(newField());
		await user.type(getByTestId('comment-input'), 'Half a thought');

		await user.keyboard('{Escape}');
		expect(getByTestId('discard-dialog').textContent).toContain('Discard this comment?');
		expect(onCancel).not.toHaveBeenCalled();

		await user.click(getByTestId('confirm-go-ahead'));
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('keeps the words, and the field, when the reader keeps writing', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId, onCancel } = drawnPuttingAway(newField());
		await user.type(getByTestId('comment-input'), 'Half a thought');

		await user.click(getByTestId('cancel-comment'));
		await user.click(getByTestId('confirm-keep'));

		expect(onCancel).not.toHaveBeenCalled();
		expect(queryByTestId('discard-dialog')).toBeNull();
		expect((getByTestId('comment-input') as HTMLTextAreaElement).value).toBe('Half a thought');
	});

	it('leaves Escape to an input method composing a word in it', async () => {
		const { getByTestId, queryByTestId, onCancel } = drawnPuttingAway(newField());
		const input = getByTestId('comment-input');

		await fireEvent.keyDown(input, { key: 'Escape', isComposing: true });

		expect(queryByTestId('discard-dialog')).toBeNull();
		expect(onCancel).not.toHaveBeenCalled();
	});

	it('leaves Ctrl+Enter to an input method composing a word in it', async () => {
		const user = userEvent.setup();
		const { getByTestId } = drawnSaving(newField());
		const input = getByTestId('comment-input');
		await user.type(input, 'Half');

		await fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true, isComposing: true });

		expect(review.threads.count).toBe(0);
	});

	it('closes an empty field on Escape without asking', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId, onCancel } = drawnPuttingAway(newField());
		getByTestId('comment-input').focus();

		await user.keyboard('{Escape}');

		expect(queryByTestId('discard-dialog')).toBeNull();
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('asks before dropping a screenshot pasted into it', async () => {
		keepingImages();
		const user = userEvent.setup();
		const { getByTestId, findByTestId, onCancel } = drawnPuttingAway(newField());
		await paste(getByTestId('comment-input'), screenshot());
		await findByTestId('attached-image');

		await user.click(getByTestId('cancel-comment'));

		expect(getByTestId('discard-dialog')).toBeTruthy();
		expect(onCancel).not.toHaveBeenCalled();
	});

	it('puts away an edit nothing was changed in without asking', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId, onCancel } = drawnPuttingAway(editOf({ body: 'As it was' }));

		await user.click(getByTestId('cancel-comment'));

		expect(queryByTestId('discard-dialog')).toBeNull();
		expect(onCancel).toHaveBeenCalledOnce();
	});

	it('asks before dropping an edit whose words were changed', async () => {
		const user = userEvent.setup();
		const { getByTestId, onCancel } = drawnPuttingAway(editOf({ body: 'As it was' }));

		await user.type(getByTestId('comment-input'), ', and more');
		await user.click(getByTestId('cancel-comment'));

		expect(getByTestId('discard-dialog')).toBeTruthy();
		expect(onCancel).not.toHaveBeenCalled();
	});

	it('asks before dropping words a reload brought back, whatever the field began from', async () => {
		const user = userEvent.setup();
		newField().text = 'Written before the reload';
		leavePage();
		review = openReview();
		const [restored] = review.threads.writing.onLinesOf('a.ts');
		const { getByTestId, onCancel } = drawnPuttingAway(restored);

		await user.click(getByTestId('cancel-comment'));

		expect(getByTestId('discard-dialog')).toBeTruthy();
		expect(onCancel).not.toHaveBeenCalled();
	});
});
