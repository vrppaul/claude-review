import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import CommentBox from '$lib/components/CommentBox.svelte';

describe('CommentBox', () => {
	it('calls onSave with trimmed text when Comment button is clicked', async () => {
		const onSave = vi.fn();
		const { getByTestId } = render(CommentBox, {
			props: { onSave, onCancel: vi.fn(), startLine: 5 }
		});

		const input = getByTestId('comment-input') as HTMLTextAreaElement;
		await userEvent.type(input, '  Fix this  ');
		await userEvent.click(getByTestId('save-comment'));

		expect(onSave).toHaveBeenCalledWith('Fix this');
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
