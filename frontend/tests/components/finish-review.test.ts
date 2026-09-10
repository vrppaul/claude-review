import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FinishReview from '$lib/components/FinishReview.svelte';
import { reviewStore } from '$lib/stores/review.svelte';
import { commentStore } from '$lib/stores/comments.svelte';

/** The count as it reads, without the template's line breaks. */
function count(element: HTMLElement): string {
	return element.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

const props = {
	submitting: false,
	onSubmit: vi.fn(),
	onSendRound: vi.fn(),
	onEnd: vi.fn(),
	onClose: vi.fn()
};

describe('finishing a review', () => {
	beforeEach(() => {
		commentStore.clear();
		reviewStore.clear();
	});

	it('shows inline comment count when comments exist', () => {
		commentStore.add('file.ts', 'new', 1, 1, 'fix this');
		commentStore.add('file.ts', 'new', 5, 5, 'and this');

		const { getByTestId } = render(FinishReview, { props });

		expect(count(getByTestId('finish-count'))).toBe('2 comments');
	});

	it('shows singular label for one comment', () => {
		commentStore.add('file.ts', 'new', 1, 1, 'fix');

		const { getByTestId } = render(FinishReview, { props });

		expect(count(getByTestId('finish-count'))).toBe('1 comment');
	});

	it('says a summary alone is a review when nothing is written', () => {
		const { queryByTestId, getByText } = render(FinishReview, { props });

		expect(queryByTestId('finish-comment')).toBeNull();
		expect(getByText(/A summary on its own is a review too/)).toBeTruthy();
	});

	it('counts what is still unsent once rounds are being sent', () => {
		reviewStore.attachAnswerer();
		commentStore.add('file.ts', 'new', 1, 1, 'fix');

		const { getByTestId } = render(FinishReview, { props });

		expect(count(getByTestId('finish-count'))).toBe('1 unsent of 1');
		expect(getByTestId('modal-submit').textContent).toContain('Send round');
		expect(getByTestId('end-review')).toBeTruthy();
	});

	it('shows each comment in full before it is sent', () => {
		const long =
			'This reads the clock twice per call, so a sweep can see two different ' +
			'instants and drop a session that was alive when it started.';
		commentStore.add('src/app.ts', 'new', 42, 42, long);

		const { getByText, getByTestId } = render(FinishReview, { props });

		// The last screen before sending is the wrong place to truncate
		expect(getByText(long)).toBeTruthy();
		expect(getByTestId('modal-comment-ref').textContent).toContain('src/app.ts');
	});

	it('disables submit when no content', () => {
		const { getByTestId } = render(FinishReview, { props });

		const btn = getByTestId('modal-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('enables submit when review body is typed', async () => {
		const { getByTestId } = render(FinishReview, { props });

		await userEvent.type(getByTestId('review-body'), 'General feedback');

		const btn = getByTestId('modal-submit') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});

	it('calls onSubmit when submit button is clicked', async () => {
		const onSubmit = vi.fn();
		commentStore.add('file.ts', 'new', 1, 1, 'fix');

		const { getByTestId } = render(FinishReview, { props: { ...props, onSubmit } });

		await userEvent.click(getByTestId('modal-submit'));

		expect(onSubmit).toHaveBeenCalled();
	});

	it('closes on a click anywhere else, leaving the review where it was', async () => {
		const onClose = vi.fn();
		const { getByTestId } = render(FinishReview, { props: { ...props, onClose } });

		await userEvent.click(getByTestId('finish-backdrop'));

		expect(onClose).toHaveBeenCalled();
	});
});

describe('the line a comment sits on, before it is sent', () => {
	beforeEach(() => {
		commentStore.clear();
		reviewStore.clear();
	});

	it('marks a comment that sits on a removed line', () => {
		commentStore.add('src/app.ts', 'old', 42, 42, 'why was this dropped');

		const { getByTestId } = render(FinishReview, { props });

		expect(getByTestId('modal-comment-ref').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'src/app.ts · Removed line 42'
		);
	});

	it('leaves a comment on the current version unmarked', () => {
		commentStore.add('src/app.ts', 'new', 42, 47, 'tighten this');

		const { getByTestId } = render(FinishReview, { props });

		expect(getByTestId('modal-comment-ref').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'src/app.ts · Lines 42-47'
		);
	});
});
