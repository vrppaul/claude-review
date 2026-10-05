import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentBox from '$lib/components/CommentBox.svelte';
import { diffStore } from '$lib/stores/diff.svelte';

describe('CommentBox', () => {
	it('calls onSave with trimmed text when Comment button is clicked', async () => {
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, {
			props: { onSave, onCancel: vi.fn(), startLine: 5 }
		});

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		await userEvent.type(input, '  Fix this  ');
		await userEvent.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Fix this', 'note', []);
	});

	it('disables Comment button when input is empty', () => {
		const { getByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn() }
		});

		const btn = getByTestId('save-comment') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('calls onCancel when Cancel is clicked', async () => {
		const onCancel = vi.fn();
		const { getByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel }
		});

		await userEvent.click(getByTestId('cancel-comment'));

		expect(onCancel).toHaveBeenCalled();
	});

	it('shows line label for single line', () => {
		const { getByText } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 42, endLine: 42 }
		});

		expect(getByText('Line 42')).toBeTruthy();
	});

	it('shows line range label for multi-line', () => {
		const { getByText } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 10, endLine: 15 }
		});

		expect(getByText('Lines 10-15')).toBeTruthy();
	});

	it('populates textarea with initialBody', () => {
		const { getByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), initialBody: 'existing text' }
		});

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		expect(input.value).toBe('existing text');
	});
});

describe('suggesting a replacement', () => {
	it('starts the suggestion from the lines being commented on', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, {
			props: {
				onSave: vi.fn(),
				onCancel: vi.fn(),
				startLine: 3,
				endLine: 4,
				suggestFrom: ['    if x:', '        return 1']
			}
		});

		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('```suggestion\n    if x:\n        return 1\n```');
	});

	it('keeps what was already written above the suggestion', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, {
			props: {
				onSave: vi.fn(),
				onCancel: vi.fn(),
				startLine: 3,
				suggestFrom: ['x = 1']
			}
		});

		await user.type(getByTestId('comment-input'), 'Name it after the unit');
		await user.click(getByTestId('suggest-change'));

		const value = (getByTestId('comment-input') as HTMLTextAreaElement).value;
		expect(value).toBe('Name it after the unit\n\n```suggestion\nx = 1\n```');
	});

	it('offers nothing to suggest when no lines were given', () => {
		const { queryByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 3 }
		});

		expect(queryByTestId('suggest-change')).toBeNull();
	});

	it('will not start a second suggestion in one comment', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 3, suggestFrom: ['x = 1'] }
		});

		await user.click(getByTestId('suggest-change'));

		expect((getByTestId('suggest-change') as HTMLButtonElement).disabled).toBe(true);
	});
});

describe('how a comment is meant', () => {
	it('is an ordinary note unless said otherwise', async () => {
		const user = userEvent.setup();
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, {
			props: { onSave, onCancel: vi.fn(), startLine: 1 }
		});

		await user.type(getByTestId('comment-input'), 'Reads well');
		await user.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Reads well', 'note', []);
	});

	it('can be marked as a question', async () => {
		const user = userEvent.setup();
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, {
			props: { onSave, onCancel: vi.fn(), startLine: 1 }
		});

		await user.click(getByTestId('severity-question'));
		await user.type(getByTestId('comment-input'), 'Is this reachable?');
		await user.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Is this reachable?', 'question', []);
	});

	it('reopens for editing with the mark it was saved under', async () => {
		const { getByTestId } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 1, initialSeverity: 'blocker' }
		});

		expect(getByTestId('severity-blocker').getAttribute('aria-pressed')).toBe('true');
	});
});

describe('images in a comment', () => {
	const LIMITS = { max_image_bytes: 10 * 1024 * 1024, max_images_per_message: 10 };

	function screenshot(): File {
		return new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], 'screen.png', {
			type: 'image/png'
		});
	}

	function imageFetch(imageId: string) {
		const mock = vi.fn((url: string) =>
			Promise.resolve({
				ok: true,
				json: () => Promise.resolve(url === '/api/images' ? { image_id: imageId } : {})
			})
		);
		vi.stubGlobal('fetch', mock);
		return mock;
	}

	beforeEach(() => {
		diffStore.clear();
		diffStore.setImageLimits(LIMITS);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('saves a pasted screenshot as the whole comment', async () => {
		imageFetch('4f.png');
		const onSave = vi.fn();
		const { getByTestId, findByTestId } = render(CommentBox, {
			props: { onSave, onCancel: vi.fn(), startLine: 5 }
		});

		await fireEvent.paste(getByTestId('comment-input'), {
			clipboardData: { files: [screenshot()] }
		});
		await findByTestId('attached-image');
		await userEvent.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('', 'note', ['4f.png']);
	});

	it('lets the server drop what was pasted when the field closes unsent', async () => {
		// Cancel, a click on another line, a folded thread: each closes the field
		const fetchMock = imageFetch('4f.png');
		const { getByTestId, findByTestId, unmount } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 5 }
		});

		await fireEvent.paste(getByTestId('comment-input'), {
			clipboardData: { files: [screenshot()] }
		});
		await findByTestId('attached-image');
		unmount();

		const [url, init] = fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit];
		expect(url).toBe('/api/images/4f.png');
		expect(init.method).toBe('DELETE');
	});

	it('keeps what was pasted once the comment is saved', async () => {
		const fetchMock = imageFetch('4f.png');
		const { getByTestId, findByTestId, unmount } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), startLine: 5 }
		});

		await fireEvent.paste(getByTestId('comment-input'), {
			clipboardData: { files: [screenshot()] }
		});
		await findByTestId('attached-image');
		await userEvent.click(getByTestId('save-comment'));
		unmount();

		expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/images']);
	});

	it('leaves the images a comment already had when an edit closes unsent', async () => {
		const fetchMock = imageFetch('4f.png');
		const { unmount } = render(CommentBox, {
			props: { onSave: vi.fn(), onCancel: vi.fn(), initialBody: 'This', initialImages: ['kept.png'] }
		});

		unmount();

		expect(fetchMock).not.toHaveBeenCalled();
	});
});
