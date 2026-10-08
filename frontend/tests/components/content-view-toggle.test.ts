import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ContentViewToggle from '$lib/components/ContentViewToggle.svelte';
import { diffStore } from '$lib/stores/diff.svelte';

describe('choosing how a markdown file is shown', () => {
	it('offers the raw text, the preview, and both side by side', () => {
		const { getByTestId } = render(ContentViewToggle);

		expect(getByTestId('view-mode-raw')).toBeTruthy();
		expect(getByTestId('view-mode-preview')).toBeTruthy();
		expect(getByTestId('view-mode-side-by-side')).toBeTruthy();
	});

	it('starts on the raw text', () => {
		const { getByTestId } = render(ContentViewToggle);

		expect(getByTestId('view-mode-raw').getAttribute('aria-pressed')).toBe('true');
		expect(getByTestId('view-mode-preview').getAttribute('aria-pressed')).toBe('false');
	});

	it('shows the preview once it is picked', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-preview'));

		expect(diffStore.contentViewMode).toBe('preview');
	});

	it('shows both side by side once that is picked', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-side-by-side'));

		expect(diffStore.contentViewMode).toBe('side-by-side');
	});

	it('shows which mode is chosen', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-preview'));

		expect(getByTestId('view-mode-raw').getAttribute('aria-pressed')).toBe('false');
		expect(getByTestId('view-mode-preview').getAttribute('aria-pressed')).toBe('true');
	});
});
