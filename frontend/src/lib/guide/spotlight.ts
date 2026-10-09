/**
 * Finding what a tour step points at on the page, and following it.
 *
 * Steps name places by `data-tour`. Where a place is, and whether it is on
 * the page at all, is read from the page itself; what the reader did is
 * not — comment fields say that themselves.
 */

/** A rectangle in viewport pixels. */
export interface Frame {
	left: number;
	top: number;
	width: number;
	height: number;
}

// Room left between the light's edge and what it lights
const SPOTLIGHT_PADDING = 4;

function selectorFor(name: string): string {
	return `[data-tour="${name}"]`;
}

function hasSize(rect: DOMRect): boolean {
	return rect.width > 0 && rect.height > 0;
}

function inViewport(rect: DOMRect): boolean {
	return (
		hasSize(rect) && rect.bottom > 0 && rect.right > 0 && rect.top < window.innerHeight && rect.left < window.innerWidth
	);
}

/**
 * The element a step means by a name.
 *
 * Some names are shared — every line number is a `line-number` — and the
 * one meant is the first the reader can see, falling back to the first that
 * is drawn at all. One that takes no room on the page is not there.
 */
function elementFor(name: string): HTMLElement | null {
	const drawn = Array.from(document.querySelectorAll<HTMLElement>(selectorFor(name))).filter((element) =>
		hasSize(element.getBoundingClientRect())
	);
	return drawn.find((element) => inViewport(element.getBoundingClientRect())) ?? drawn[0] ?? null;
}

/** Whether anything is drawn on the page under a name; the first drawn is enough. */
function isDrawn(name: string): boolean {
	for (const element of document.querySelectorAll<HTMLElement>(selectorFor(name))) {
		if (hasSize(element.getBoundingClientRect())) return true;
	}
	return false;
}

/** The elements drawn for some names, one per name at most. */
function elementsFor(names: string[]): HTMLElement[] {
	return names.map(elementFor).filter((element): element is HTMLElement => element !== null);
}

function frameOf(elements: HTMLElement[]): Frame | null {
	const rects = elements.map((element) => element.getBoundingClientRect());
	if (rects.length === 0) return null;

	const left = Math.min(...rects.map((rect) => rect.left)) - SPOTLIGHT_PADDING;
	const top = Math.min(...rects.map((rect) => rect.top)) - SPOTLIGHT_PADDING;
	const right = Math.max(...rects.map((rect) => rect.right)) + SPOTLIGHT_PADDING;
	const bottom = Math.max(...rects.map((rect) => rect.bottom)) + SPOTLIGHT_PADDING;
	return { left, top, width: right - left, height: bottom - top };
}

export function sameFrame(first: Frame | null, second: Frame | null): boolean {
	return (
		first === second ||
		(first !== null &&
			second !== null &&
			first.left === second.left &&
			first.top === second.top &&
			first.width === second.width &&
			first.height === second.height)
	);
}

/** Bring the first place into view, if the reader has scrolled away from it. */
export function reveal(names: string[]): void {
	const first = names.map(elementFor).find((element) => element !== null);
	if (first && !inViewport(first.getBoundingClientRect())) {
		first.scrollIntoView({ block: 'center' });
	}
}

/**
 * Calls back, at most once a frame, whenever something on the page may have
 * changed: an element added or removed, the window or the page resized, or
 * one of the elements it is told to watch resized.
 *
 * Measuring is left to whoever listens: the line numbers of a large diff are
 * thousands of elements to look through, and once a frame is often enough.
 */
class PageChanges {
	readonly #onChange: () => void;
	readonly #mutations: MutationObserver;
	readonly #resizes: ResizeObserver;
	#pending = 0;
	#watched: HTMLElement[] = [];

	constructor(onChange: () => void) {
		this.#onChange = onChange;
		this.#mutations = new MutationObserver(this.notice);
		this.#resizes = new ResizeObserver(this.notice);
		this.#mutations.observe(document.body, { childList: true, subtree: true });
		this.#resizes.observe(document.body);
		window.addEventListener('resize', this.notice);
	}

	/** Something may have changed: call back once the frame is drawn. */
	readonly notice = (): void => {
		if (this.#pending) return;
		this.#pending = requestAnimationFrame(this.#changed);
	};

	/** Also call back when any of these elements changes size, and stop watching the ones before. */
	watchSizeOf(elements: HTMLElement[]): void {
		const same =
			elements.length === this.#watched.length && elements.every((element, index) => element === this.#watched[index]);
		if (same) return;
		this.#resizes.disconnect();
		this.#resizes.observe(document.body);
		for (const element of elements) this.#resizes.observe(element);
		this.#watched = elements;
	}

	stop(): void {
		cancelAnimationFrame(this.#pending);
		this.#mutations.disconnect();
		this.#resizes.disconnect();
		window.removeEventListener('resize', this.notice);
	}

	readonly #changed = (): void => {
		this.#pending = 0;
		this.#onChange();
	};
}

/**
 * Keeps a frame around some places as the page moves under them.
 *
 * Measured whenever the page changes and whenever it scrolls. The lit
 * elements are watched for size themselves: a comment field grows as it is
 * typed into, and a dragged panel edge changes nothing else.
 */
export class PageWatcher {
	readonly #names: string[];
	readonly #onFrame: (frame: Frame | null) => void;
	readonly #changes: PageChanges;

	constructor(names: string[], onFrame: (frame: Frame | null) => void) {
		this.#names = names;
		this.#onFrame = onFrame;
		this.#changes = new PageChanges(() => this.#measure());
		window.addEventListener('scroll', this.#changes.notice, { capture: true, passive: true });
		this.#measure();
	}

	stop(): void {
		this.#changes.stop();
		window.removeEventListener('scroll', this.#changes.notice, { capture: true });
	}

	#measure(): void {
		const lit = elementsFor(this.#names);
		this.#changes.watchSizeOf(lit);
		this.#onFrame(frameOf(lit));
	}
}

/**
 * Tells which of some places are drawn on the page, whenever that changes.
 *
 * Scrolling draws nothing new, so only changes to the page are measured.
 */
export class TargetWatcher<Name extends string> {
	readonly #names: readonly Name[];
	readonly #onTargets: (drawn: ReadonlySet<Name>) => void;
	readonly #changes: PageChanges;
	#drawn: ReadonlySet<Name> | null = null;

	constructor(names: readonly Name[], onTargets: (drawn: ReadonlySet<Name>) => void) {
		this.#names = names;
		this.#onTargets = onTargets;
		this.#changes = new PageChanges(() => this.#measure());
		this.#measure();
	}

	stop(): void {
		this.#changes.stop();
	}

	#measure(): void {
		const drawn: ReadonlySet<Name> = new Set(this.#names.filter(isDrawn));
		if (this.#drawn !== null && sameMembers(drawn, this.#drawn)) return;
		this.#drawn = drawn;
		this.#onTargets(drawn);
	}
}

function sameMembers<Member>(first: ReadonlySet<Member>, second: ReadonlySet<Member>): boolean {
	return first.size === second.size && [...first].every((member) => second.has(member));
}
