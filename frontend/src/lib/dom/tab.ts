/**
 * What the review says about itself from a tab strip.
 *
 * An answer can arrive while the review is in a background tab, where none
 * of the page is visible. The title carries the count and the icon takes a
 * dot — both are the browser's own furniture, and neither needs a
 * permission prompt the way a system notification would.
 */

import quietIcon from '$lib/assets/tab-icon.svg';
import unreadIcon from '$lib/assets/tab-icon-unread.svg';

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
	iconLink().href = unread > 0 ? unreadIcon : quietIcon;
}
