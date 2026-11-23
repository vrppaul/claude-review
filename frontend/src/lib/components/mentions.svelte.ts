/**
 * The picker a panel message points at threads and files with: opened by
 * typing @, narrowed by what follows it, and closed by taking one or by
 * typing past it.
 *
 * Threads come first — most questions are about something already
 * commented on — and then the files themselves, so a file nobody has marked
 * can be pointed at too: the agent can name any file, and the reader should
 * be able to as well.
 */

import { anchorToken } from '$lib/anchors/views';
import { fileToken, mentionBeingTyped, type TypedText } from '$lib/anchors/mentions';
import type { DiffFile, Thread } from '$lib/types';

/** A thread or a file a message can point at. */
export type Mentionable = ThreadMention | FileMention;
export interface ThreadMention {
	kind: 'thread';
	thread: Thread;
}
export interface FileMention {
	kind: 'file';
	path: string;
}

/** One the picker lists, with its place among all it lists, which the keys and the field's highlight count by. */
export interface Listed<Pick extends Mentionable> {
	pick: Pick;
	index: number;
}

/** What the picker offers from: the review's threads and files, as they stand. */
export interface Offered {
	threads: () => Thread[];
	files: () => DiffFile[];
}

/** Whether what was typed after the @ is in what a candidate is known by. */
function answersTo(query: string, knownBy: string): boolean {
	return knownBy.toLowerCase().includes(query.toLowerCase());
}

/** The token a message mentions a candidate by. */
export function tokenOf(pick: Mentionable): string {
	return pick.kind === 'thread' ? anchorToken(pick.thread.anchor) : fileToken(pick.path);
}

/** The id of an option in the list, which the field names while that option is highlighted. */
export function optionIdOf(listId: string, index: number): string {
	return `${listId}-option-${index}`;
}

export class Mentions {
	#open = $state(false);
	// What has been typed since the @
	#query = $state('');
	#highlighted = $state(0);
	readonly #threads: Listed<ThreadMention>[];
	readonly #files: Listed<FileMention>[];
	readonly #candidates: Mentionable[];

	constructor(offered: Offered) {
		this.#threads = $derived(
			offered
				.threads()
				.filter((thread) => answersTo(this.#query, `${anchorToken(thread.anchor)} ${thread.body}`))
				.map((thread, index) => ({ pick: { kind: 'thread', thread }, index }))
		);
		// The files after the threads, counted on from the last of them
		this.#files = $derived(
			offered
				.files()
				.filter((file) => answersTo(this.#query, file.path))
				.map((file, at) => ({ pick: { kind: 'file', path: file.path }, index: this.#threads.length + at }))
		);
		this.#candidates = $derived([...this.#threads, ...this.#files].map((listed) => listed.pick));
	}

	/** Whether the picker is on screen: open, with something in it to pick. */
	get shown(): boolean {
		return this.#open && this.#candidates.length > 0;
	}

	/** The threads listed, first. */
	get threads(): Listed<ThreadMention>[] {
		return this.#threads;
	}

	/** The files listed, after the threads. */
	get files(): Listed<FileMention>[] {
		return this.#files;
	}

	get highlighted(): number {
		return this.#highlighted;
	}

	/** The candidate Enter would take. */
	get chosen(): Mentionable | undefined {
		return this.#candidates[this.#highlighted];
	}

	/** Watch what is being typed for an @ that has not been finished yet. */
	follow(typed: TypedText): void {
		const query = mentionBeingTyped(typed);
		this.#open = query !== null;
		this.#query = query ?? '';
		this.#highlighted = 0;
	}

	/** Open on everything, as if an @ had just been typed. */
	openOnEverything(): void {
		this.#open = true;
		this.#query = '';
		this.#highlighted = 0;
	}

	close(): void {
		this.#open = false;
	}

	/** Move the highlight down or up the list, round from one end to the other. */
	step(direction: 1 | -1): void {
		const count = this.#candidates.length;
		if (count > 0) this.#highlighted = (this.#highlighted + direction + count) % count;
	}
}
