import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewModal from '$lib/components/ReviewModal.svelte';
import { commentStore } from '$lib/stores/comments.svelte';

describe('ReviewModal', () => {
	beforeEach(() => {
		commentStore.clear();
	});

	it('shows inline comment count when comments exist', () => {
		commentStore.add('file.ts', 'new', 1, 1, 'fix this');
		commentStore.add('file.ts', 'new', 5, 5, 'and this');

		const { getByText } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		expect(getByText('2 inline comments')).toBeTruthy();
	});

	it('shows singular label for one comment', () => {
		commentStore.add('file.ts', 'new', 1, 1, 'fix');

		const { getByText } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		expect(getByText('1 inline comment')).toBeTruthy();
	});

	it('hides comment list when no inline comments', () => {
		const { queryByText } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		expect(queryByText('inline comment')).toBeNull();
	});

	it('shows each comment in full before it is sent', () => {
		const long =
			'This reads the clock twice per call, so a sweep can see two different ' +
			'instants and drop a session that was alive when it started.';
		commentStore.add('src/app.ts', 'new', 42, 42, long);

		const { getByText, getByTestId } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		// The last screen before sending is the wrong place to truncate
		expect(getByText(long)).toBeTruthy();
		expect(getByTestId('modal-comment-ref').textContent).toContain('src/app.ts');
	});

	it('disables submit when no content', () => {
		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		const btn = getByTestId('modal-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('enables submit when review body is typed', async () => {
		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose: vi.fn() }
		});

		await userEvent.type(getByTestId('review-body'), 'General feedback');

		const btn = getByTestId('modal-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});

	it('calls onSubmit when submit button is clicked', async () => {
		const onSubmit = vi.fn();
		commentStore.add('file.ts', 'new', 1, 1, 'fix');

		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit, onClose: vi.fn() }
		});

		await userEvent.click(getByTestId('modal-submit'));

		expect(onSubmit).toHaveBeenCalled();
	});

	it('calls onClose when Cancel is clicked', async () => {
		const onClose = vi.fn();
		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit: vi.fn(), onClose }
		});

		await userEvent.click(getByTestId('cancel-modal'));

		expect(onClose).toHaveBeenCalled();
	});
});

describe('ReviewModal line references', () => {
	beforeEach(() => {
		commentStore.clear();
	});

	it('marks a comment that sits on a removed line', () => {
		commentStore.add('src/app.ts', 'old', 42, 42, 'why was this dropped');

		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit: () => {}, onClose: () => {} }
		});

		expect(getByTestId('modal-comment-ref').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'src/app.ts · Removed line 42'
		);
	});

	it('leaves a comment on the current version unmarked', () => {
		commentStore.add('src/app.ts', 'new', 42, 47, 'tighten this');

		const { getByTestId } = render(ReviewModal, {
			props: { onSubmit: () => {}, onClose: () => {} }
		});

		expect(getByTestId('modal-comment-ref').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'src/app.ts · Lines 42-47'
		);
	});
});
