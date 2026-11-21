/**
 * Where the names the tree of files lists are defined and used, asked from
 * the icon at the end of each name's row: which names can be asked about
 * there, whether a name's pane is open, and a press that asks or closes it.
 * The rows draw the icons; TreeNameLookup draws the pane.
 */

import { NameLookup } from '$lib/review/name-lookup.svelte';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { TouchedName } from '$lib/types';
import { AskedFromTheTree } from './tree-name-asked';

export class LookupFromTheTree extends NameLookup<AskedFromTheTree> {
	readonly #diff: ReviewDiff;

	/** @param diff the diff on screen, whose take a name is asked in and whose numbering says which can be asked */
	constructor(diff: ReviewDiff) {
		super();
		this.#diff = diff;
	}

	/**
	 * Whether a name can be looked up from its row: one the change removed stands on the old side, which is the
	 * review's own file only while the diff on screen is numbered as the review's own, as the gesture in the code is.
	 */
	offers(name: TouchedName): boolean {
		return name.side === 'new' || this.#diff.numbering === 'the-reviews';
	}

	/** Whether the pane of a name is open, or its window. */
	isOpen(name: TouchedName): boolean {
		return this.asked?.from.name === name;
	}

	/**
	 * Ask where a name of a file is defined and used, from the icon pressed; a press while its pane is open closes it.
	 *
	 * @param fileRow the row of the name's file as it is drawn now, which takes the keyboard once the icon is gone
	 */
	toggle(path: string, name: TouchedName, icon: HTMLElement, fileRow: () => HTMLElement | null): void {
		if (this.isOpen(name)) {
			this.close();
			return;
		}
		const place = { path, side: name.side, line: name.line, column: name.column };
		this.ask(place, name.name, new AskedFromTheTree(name, icon, fileRow), this.#diff.takeOnScreen);
	}
}
