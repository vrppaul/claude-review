/**
 * A name asked about from its row in the tree of files, by the icon at the
 * row's end. The pane stands by the icon, drawn apart from it over the
 * column, so the column's list does not cut it; it closes once the row is
 * drawn no more, its file's names folded or the diff read another way, and
 * the keyboard then goes to the row of the name's file. It closes too once
 * the tree scrolls the icon out of sight: drawn over the page, the pane
 * would follow it out of the window.
 */

import { seenAtAll } from '$lib/dom/in-sight';
import type { AskedFrom } from '$lib/review/name-lookup.svelte';
import type { TouchedName } from '$lib/types';

export class AskedFromTheTree implements AskedFrom {
	/** The name as the tree lists it, whose icon is drawn pressed while its pane or its window is open. */
	readonly name: TouchedName;
	readonly standsBy: { control: HTMLElement };
	readonly #icon: HTMLElement;
	readonly #fileRow: () => HTMLElement | null;

	/**
	 * @param name the name as the tree lists it
	 * @param icon the icon pressed at the end of its row
	 * @param fileRow the row of its file in the tree, as it is drawn now
	 */
	constructor(name: TouchedName, icon: HTMLElement, fileRow: () => HTMLElement | null) {
		this.name = name;
		this.standsBy = { control: icon };
		this.#icon = icon;
		this.#fileRow = fileRow;
	}

	readonly standsThere = (): boolean => this.#icon.isConnected && seenAtAll(this.#icon);

	readonly keyboardTo = (): HTMLElement | null => (this.#icon.isConnected ? this.#icon : this.#fileRow());
}
