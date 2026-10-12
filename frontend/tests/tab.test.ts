import { afterEach, describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { markTab } from '$lib/dom/tab';

const TITLE = 'repo: uncommitted changes';
// The icons as the files they are, read for what they write in them
const ICONS = ['tab-icon.svg', 'tab-icon-unread.svg'].map((name) =>
	readFileSync(join(__dirname, '../src/lib/assets', name), 'utf8')
);
// A colour written out rather than named: #rgb to #rrggbbaa, or a function of channels
const WRITTEN_COLOUR = /#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i;
// What the page's tokens say, as a test sets them: jsdom reads no stylesheet
const UNREAD = '#7a5cc8';
const FAINT = '#6f7b8c';

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

describe('the colours of the tab icon', () => {
	afterEach(() => {
		document.documentElement.removeAttribute('style');
	});

	it('are named by their tokens in the icons, never written out there', () => {
		for (const icon of ICONS) expect(icon).not.toMatch(WRITTEN_COLOUR);
		expect(ICONS[1]).toContain('var(--cr-unread)');
	});

	it('are written in from the page as the icon is set: the dot in the colour of what is unread', () => {
		document.documentElement.style.setProperty('--cr-unread', UNREAD);
		document.documentElement.style.setProperty('--cr-faint', FAINT);

		markTab(1, TITLE);

		const drawn = decodeURIComponent(tabIcon() ?? '');
		expect(drawn).toContain(`fill="${UNREAD}"`);
		expect(drawn).toContain(`stroke="${FAINT}"`);
		expect(drawn).not.toContain('var(');
	});
});
