/**
 * Pointing at a part of the page, as the reader's feedback names the part it
 * is about.
 *
 * A part is named by the test ids the page gave it and the few it stands
 * in: names the page wrote, never words the reader's review holds, so a
 * part of their code, a path or a branch is named by what it is and never
 * by what it says. Every control carries one of its own; words and code are
 * named by what holds them.
 *
 * While the reader points, the page sees none of it: a press anywhere but
 * the card the reader points from is taken before the page hears it, and
 * names the part under it. From the keyboard, Tab walks the page as ever,
 * Enter takes the part the keyboard is on, and Escape stops.
 */

import { isComposingText } from '$lib/dom/keyboard';

/** A part of the page pointed at: its name, and where it stood in the window, in whole pixels. */
export interface PointedPart {
	name: string;
	left: number;
	top: number;
	width: number;
	height: number;
}

/** What pointing tells whoever points: the part under the pointer or the keyboard, the one taken, and the end. */
export interface Pointing {
	over: (part: PointedPart) => void;
	take: (part: PointedPart) => void;
	stop: () => void;
}

// How many test ids a part is named by: its own and those it stands in, the outermost first
const NAMES_IN_A_PART = 3;
// What stands between them
const WITHIN = ' › ';
const TEST_ID = 'data-testid';
// The events a press is made of, every one of them taken before the page hears it; the last takes the part
const PRESSES = ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'] as const;
const TAKEN_ON = 'click';
const TAKE_KEY = 'Enter';
const STOP_KEY = 'Escape';

/** The element named by a test id that an element stands in, itself first; none outside every one. */
function namedHolder(element: Element | null): Element | null {
	return element?.closest(`[${TEST_ID}]`) ?? null;
}

/** The test ids of a part and of the few it stands in, the outermost first. */
function namesOf(part: Element): string[] {
	const names: string[] = [];
	let holder: Element | null = part;
	while (holder && names.length < NAMES_IN_A_PART) {
		names.unshift(holder.getAttribute(TEST_ID) ?? '');
		holder = namedHolder(holder.parentElement);
	}
	return names;
}

/** The part of the page an element stands in, named and placed; none outside every part. */
function partAt(element: Element): PointedPart | null {
	const part = namedHolder(element);
	if (!part) return null;
	const box = part.getBoundingClientRect();
	return {
		name: namesOf(part).join(WITHIN),
		left: Math.round(box.left),
		top: Math.round(box.top),
		width: Math.round(box.width),
		height: Math.round(box.height)
	};
}

/** Stop an event from reaching the page, and from doing what the browser does with it. */
function keptFromThePage(event: Event): void {
	event.preventDefault();
	event.stopPropagation();
}

/**
 * The reader pointing at the page until a part is taken or they stop, from
 * everywhere but where they point from, which goes on answering as ever.
 */
export class PartPicker {
	readonly #pointedFrom: HTMLElement;
	readonly #pointing: Pointing;
	readonly #listening = new AbortController();

	constructor(pointedFrom: HTMLElement, pointing: Pointing) {
		this.#pointedFrom = pointedFrom;
		this.#pointing = pointing;
		const options = { capture: true, signal: this.#listening.signal };
		window.addEventListener('pointerover', (event) => this.#noteOver(event), options);
		window.addEventListener('focusin', (event) => this.#noteOver(event), options);
		for (const press of PRESSES) window.addEventListener(press, (event) => this.#takePress(event), options);
		window.addEventListener('keydown', (event) => this.#takeKey(event), options);
	}

	/** Stop pointing, taking nothing. */
	stop(): void {
		this.#listening.abort();
	}

	/** An element the page stands in, apart from where the reader points from; none for anything else. */
	#pointedAt(target: EventTarget | null): Element | null {
		return target instanceof Element && !this.#pointedFrom.contains(target) ? target : null;
	}

	/** Say the part under the pointer, or the one the keyboard went to. */
	#noteOver(event: Event): void {
		const target = this.#pointedAt(event.target);
		const part = target && partAt(target);
		if (part) this.#pointing.over(part);
	}

	/** Take every press away from the page; the click that ends one takes the part pressed. */
	#takePress(event: Event): void {
		const target = this.#pointedAt(event.target);
		if (!target) return;
		keptFromThePage(event);
		const part = event.type === TAKEN_ON ? partAt(target) : null;
		if (part) this.#pointing.take(part);
	}

	/** Enter takes the part the keyboard is on, Escape stops: neither reaches the page. */
	#takeKey(event: KeyboardEvent): void {
		if (isComposingText(event)) return;
		if (event.key === STOP_KEY) {
			keptFromThePage(event);
			this.#pointing.stop();
			return;
		}
		const target = this.#pointedAt(event.target);
		if (event.key !== TAKE_KEY || !target) return;
		keptFromThePage(event);
		const part = partAt(target);
		if (part) this.#pointing.take(part);
	}
}
