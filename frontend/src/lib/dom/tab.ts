/**
 * What the review says about itself from a tab strip.
 *
 * An answer can arrive while the review is in a background tab, where none
 * of the page is visible. The title carries the count and the icon takes a
 * dot — both are the browser's own furniture, and neither needs a
 * permission prompt the way a system notification would.
 *
 * The icon names its colours by their tokens. Set as the tab's icon it is an
 * image, which reads no stylesheet, so the page writes in the value each
 * token has on the page as it sets it: every colour stays written once, in
 * tokens.css.
 */

import quietIcon from '$lib/assets/tab-icon.svg?raw';
import unreadIcon from '$lib/assets/tab-icon-unread.svg?raw';

// A colour an icon names by its token
const NAMED_COLOUR = /var\((--[a-z0-9-]+)\)/g;
// How an icon's markup is handed to the browser as an address
const SVG_ADDRESS = 'data:image/svg+xml,';

/** An icon as an address, each colour it names by token written in as the page has it now. */
function painted(icon: string): string {
	const page = getComputedStyle(document.documentElement);
	const coloured = icon.replaceAll(NAMED_COLOUR, (_named, token: string) => page.getPropertyValue(token).trim());
	return `${SVG_ADDRESS}${encodeURIComponent(coloured)}`;
}

function iconLink(): HTMLLinkElement {
	const existing = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
	if (existing) return existing;

	const link = document.createElement('link');
	link.rel = 'icon';
	document.head.appendChild(link);
	return link;
}

export function markTab(unread: number, title: string): void {
	document.title = unread > 0 ? `(${unread}) ${title}` : title;
	iconLink().href = painted(unread > 0 ? unreadIcon : quietIcon);
}
