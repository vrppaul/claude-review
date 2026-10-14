import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

/** Whoever drew the question goes on drawing it: nothing is done as it closes. */
function keptDrawn(): void {}

describe('a question the reader answered by going ahead', () => {
	it('has what was asked done once, though the dialog is shown and closed again', async () => {
		const user = userEvent.setup();
		const goneAhead = vi.fn();
		render(ConfirmDialog, {
			props: {
				question: 'Discard this comment?',
				goAhead: 'Discard',
				keep: 'Keep writing',
				onGoAhead: goneAhead,
				onClose: keptDrawn,
				testId: 'question'
			}
		});
		await user.click(screen.getByTestId('confirm-go-ahead'));
		const question = screen.getByTestId<HTMLDialogElement>('question');

		question.showModal();
		question.close();

		expect(goneAhead).toHaveBeenCalledTimes(1);
	});
});
