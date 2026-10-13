/**
 * Which part of a story the reader is in — its overview, a chapter, what it
 * leaves out — and taking them to one.
 *
 * A part is more than the sections inside it. A chapter's head, why its
 * changes belong together and where to doubt them draw no line of a file,
 * and the overview draws none at all: while those are at the top of the
 * reading area no section is being read, and no section stands for a
 * chapter's head to take the reader to. So the parts announce themselves
 * here, as sections do to `FileSections`, and are read by a band of their
 * own. A band apart, because a chapter holds its steps: read among them, the
 * chapter, which comes first on the page, would always be the one read.
 *
 * A part says where its head is too. The reader is deep in the part they
 * read once that head has left the reading area: nothing on screen then
 * says which part it is, unless the page does.
 */

import { SvelteSet } from 'svelte/reactivity';

import type { Jumps } from '$lib/dom/jump';
import { lendKeyboardToWhatRemains } from '$lib/dom/keyboard';
import { ReadingBand } from '$lib/dom/reading-band.svelte';

/** A part as it announced itself: what whoever draws it knows it by, the whole of it, and its head. */
interface Part {
	key: string;
	whole: HTMLElement;
	head: HTMLElement;
}

export class ReadingParts {
	// Every part on the page, by its key
	readonly #byKey = new Map<string, Part>();
	// And by the element that is the whole of it, so the one being read names itself
	readonly #byWhole = new Map<Element, Part>();
	// Which part the reader is in, while the reading area is watched
	readonly #band = new ReadingBand();
	// The heads in view anywhere in the reading area, while it is watched
	readonly #headsInView = new SvelteSet<Element>();
	// What watches the heads, while the reading area is watched
	#headsWatch: IntersectionObserver | null = null;
	// Where the page is taking the reader: one jump at a time, shared with whatever else takes them somewhere
	readonly #jumps: Jumps;

	/** @param jumps where the page is taking the reader, one place at a time */
	constructor(jumps: Jumps) {
		this.#jumps = jumps;
	}

	/**
	 * The part the reader is in, by its key: the one the page took them to,
	 * or the first on the page of those at the top of the reading area.
	 * None while the area is not watched, or no part is at its top.
	 */
	get beingRead(): string | null {
		return this.#partBeingRead()?.key ?? null;
	}

	/**
	 * The part the reader is deep in, by its key: the one being read, once
	 * its head has left the reading area. None while that head is in view.
	 */
	get deepIn(): string | null {
		const read = this.#partBeingRead();
		return read === null || this.#headsInView.has(read.head) ? null : read.key;
	}

	/**
	 * Say where a part is, the whole of it and its head, by the key whoever
	 * draws it knows it by. Returns how to take it back.
	 */
	register(key: string, whole: HTMLElement, head: HTMLElement): () => void {
		const part = { key, whole, head };
		this.#byKey.set(key, part);
		this.#byWhole.set(whole, part);
		this.#band.add(whole);
		this.#headsWatch?.observe(head);
		return () => this.#unregister(part);
	}

	/**
	 * Follow which part the reader is in as they scroll an area, and which
	 * heads are in view in it. Parts drawn later are watched as they arrive.
	 * Returns how to stop.
	 */
	watchInView(root: HTMLElement): () => void {
		const parts = [...this.#byKey.values()];
		const stopBand = this.#band.watch(
			root,
			parts.map((part) => part.whole)
		);
		const headsWatch = new IntersectionObserver((entries) => this.#headsMoved(entries), { root });
		this.#headsWatch = headsWatch;
		for (const part of parts) headsWatch.observe(part.head);
		return () => this.#stopWatching(stopBand, headsWatch);
	}

	/**
	 * Take the reader to a part: its head to the top at once, and the part
	 * the one being read, which they are not deep in. Nowhere, for a part
	 * that is not drawn.
	 */
	goTo(key: string): void {
		const part = this.#byKey.get(key);
		if (!part) return;
		// Where the reader is taken is its head: in view from now on, before what watches the heads has looked again
		this.#headsInView.add(part.head);
		this.#jumps.land(this.#band, part.whole, 'instant');
	}

	/**
	 * Put the keyboard on the head of the part being read, if what had it
	 * went: a bar over the part that is drawn only while the reader is deep
	 * in it. The head is where the bar's own buttons take the reader, and
	 * the next key starts from it; it is words, so it holds the keyboard
	 * only until the keyboard leaves it.
	 */
	keyboardToBeingRead(): void {
		lendKeyboardToWhatRemains(() => this.#partBeingRead()?.head);
	}

	/** The part being read, while the reading area is watched and one is at its top. */
	#partBeingRead(): Part | null {
		const whole = this.#band.earliest;
		return whole === null ? null : (this.#byWhole.get(whole) ?? null);
	}

	#headsMoved(entries: IntersectionObserverEntry[]): void {
		for (const entry of entries) {
			// What the observer noted before a part was taken away still arrives after it
			if (entry.isIntersecting && entry.target.isConnected) this.#headsInView.add(entry.target);
			else this.#headsInView.delete(entry.target);
		}
	}

	#stopWatching(stopBand: () => void, headsWatch: IntersectionObserver): void {
		stopBand();
		headsWatch.disconnect();
		if (this.#headsWatch !== headsWatch) return;
		this.#headsWatch = null;
		this.#headsInView.clear();
	}

	#unregister(part: Part): void {
		this.#band.remove(part.whole);
		this.#headsWatch?.unobserve(part.head);
		this.#headsInView.delete(part.head);
		this.#byWhole.delete(part.whole);
		if (this.#byKey.get(part.key) === part) this.#byKey.delete(part.key);
	}
}
