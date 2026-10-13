/**
 * How far the reader has got through the story: which of its parts they
 * have read through.
 *
 * The story is the review's, and no part of the reader's draft; how far
 * they got through it is theirs, and is kept with the draft. A part is
 * marked by whoever draws it, once the reader has scrolled through it:
 * every part alike, what the story leaves out too. The contents say it of
 * the parts they give a node, the overview and each chapter.
 *
 * What was read is of one story. The review says when it was told another,
 * and what was read is forgotten as the page comes to hold that one, which
 * `ReviewStory` sees to; and each run of the review is told its story anew,
 * so a draft kept in another run brings nothing read. Not guarded: where
 * the review was told another story and this page never heard so — it was
 * said in a gap the review could not hand over again — what was read of
 * the story before stands for the parts of the new one known by the same
 * names.
 */

import { SvelteSet } from 'svelte/reactivity';

/**
 * What was read through, to whoever draws a part of the story or keeps the
 * draft. Forgetting is left out: only the story, which knows when the one
 * it holds is another, forgets.
 */
export interface PartsRead {
	/** The parts read through, as the draft keeps them. */
	readonly kept: string[];
	/** Whether the reader has read a part through. */
	isRead: (part: string) => boolean;
	/** The reader has read a part through. */
	markRead: (part: string) => void;
}

export class StoryProgress implements PartsRead {
	// The parts read through, by what each is known by on the page
	readonly #read: SvelteSet<string>;

	/** @param kept the parts the reader had read through when the page was last open in this run of the review */
	constructor(kept: readonly string[]) {
		this.#read = new SvelteSet(kept);
	}

	get kept(): string[] {
		return [...this.#read];
	}

	isRead(part: string): boolean {
		return this.#read.has(part);
	}

	markRead(part: string): void {
		this.#read.add(part);
	}

	/** The story held is another: nothing of it is read yet. */
	forget(): void {
		this.#read.clear();
	}
}
