import { describe, it, expect } from 'vitest';
import { markTab } from '$lib/utils/tab';

const TITLE = 'repo: uncommitted changes';

function tabIcon(): string | undefined {
	return document.querySelector<HTMLLinkElement>('link[rel="icon"]')?.href;
}

describe('the tab of a review in the background', () => {
	it('counts what is unread in its title, and marks its icon', () => {
		markTab(0, TITLE);
		const quiet = tabIcon();

		markTab(2, TITLE);

		expect(document.title).toBe(`(2) ${TITLE}`);
		expect(tabIcon()).not.toBe(quiet);
	});

	it('says only the title once everything is read', () => {
		markTab(2, TITLE);

		markTab(0, TITLE);

		expect(document.title).toBe(TITLE);
	});
});
