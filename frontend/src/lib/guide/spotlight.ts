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
    hasSize(rect) &&
    rect.bottom > 0 &&
    rect.right > 0 &&
    rect.top < window.innerHeight &&
    rect.left < window.innerWidth
  );
}

/**
 * The element a step means by a name.
 *
 * Some names are shared — every line number is a `line-number` — and the
 * one meant is the first the reader can see, falling back to the first that
 * is drawn at all. One that takes no room on the page is not there.
 */
export function elementFor(name: string): HTMLElement | null {
  const drawn = Array.from(
    document.querySelectorAll<HTMLElement>(selectorFor(name)),
  ).filter((element) => hasSize(element.getBoundingClientRect()));
  return (
    drawn.find((element) => inViewport(element.getBoundingClientRect())) ??
    drawn[0] ??
    null
  );
}

/** Whether any of a step's places is drawn on the page. */
export function anyOnPage(names: string[]): boolean {
  return names.some((name) => elementFor(name) !== null);
}

/** The elements drawn for some names, one per name at most. */
export function elementsFor(names: string[]): HTMLElement[] {
  return names
    .map(elementFor)
    .filter((element): element is HTMLElement => element !== null);
}

/** The frame around every place that is drawn, or null for none. */
export function frameAround(names: string[]): Frame | null {
  return frameOf(elementsFor(names));
}

function frameOf(elements: HTMLElement[]): Frame | null {
  const rects = elements.map((element) => element.getBoundingClientRect());
  if (rects.length === 0) return null;

  const left = Math.min(...rects.map((rect) => rect.left)) - SPOTLIGHT_PADDING;
  const top = Math.min(...rects.map((rect) => rect.top)) - SPOTLIGHT_PADDING;
  const right =
    Math.max(...rects.map((rect) => rect.right)) + SPOTLIGHT_PADDING;
  const bottom =
    Math.max(...rects.map((rect) => rect.bottom)) + SPOTLIGHT_PADDING;
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
    first.scrollIntoView({ block: "center" });
  }
}

/**
 * Keeps a frame around some places as the page moves under them.
 *
 * Measured when something could have moved them — a scroll, the window or
 * a lit element changing size, the page changing — and at most once a
 * frame, rather than every frame: the line numbers of a large diff are
 * thousands of elements to look through. The lit elements are watched for
 * size themselves: a comment field grows as it is typed into, and a
 * dragged panel edge changes nothing else.
 */
export class PageWatcher {
  readonly #names: string[];
  readonly #onFrame: (frame: Frame | null) => void;
  readonly #mutations: MutationObserver;
  readonly #resizes: ResizeObserver;
  #pending = 0;
  #lit: HTMLElement[] = [];

  constructor(names: string[], onFrame: (frame: Frame | null) => void) {
    this.#names = names;
    this.#onFrame = onFrame;
    this.#mutations = new MutationObserver(this.#schedule);
    this.#resizes = new ResizeObserver(this.#schedule);
    this.#mutations.observe(document.body, { childList: true, subtree: true });
    this.#resizes.observe(document.body);
    window.addEventListener("scroll", this.#schedule, {
      capture: true,
      passive: true,
    });
    window.addEventListener("resize", this.#schedule);
    this.#measure();
  }

  stop() {
    cancelAnimationFrame(this.#pending);
    this.#mutations.disconnect();
    this.#resizes.disconnect();
    window.removeEventListener("scroll", this.#schedule, { capture: true });
    window.removeEventListener("resize", this.#schedule);
  }

  readonly #schedule = () => {
    if (this.#pending) return;
    this.#pending = requestAnimationFrame(this.#measure);
  };

  readonly #measure = () => {
    this.#pending = 0;
    const lit = elementsFor(this.#names);
    this.#watchSizeOf(lit);
    this.#onFrame(frameOf(lit));
  };

  #watchSizeOf(lit: HTMLElement[]) {
    const same =
      lit.length === this.#lit.length &&
      lit.every((element, index) => element === this.#lit[index]);
    if (same) return;
    this.#resizes.disconnect();
    this.#resizes.observe(document.body);
    for (const element of lit) this.#resizes.observe(element);
    this.#lit = lit;
  }
}
