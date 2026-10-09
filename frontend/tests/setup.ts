/** jsdom implements none of these; components under test rely on them. */
import { beforeEach, vi } from 'vitest';
import { leavePage } from './review';

// Every test starts from a page opened fresh: each builds its own review,
// and what one test leaves in storage, or in the draft the page holds,
// would otherwise be the next test's starting point
beforeEach(() => {
	leavePage();
	localStorage.clear();
});

/**
 * Reports everything as visible straight away. jsdom has no layout, so a real
 * observer would never fire and anything that waits to come near the viewport
 * would never render.
 */
class ImmediateIntersectionObserver implements IntersectionObserver {
	readonly root = null;
	readonly rootMargin = '';
	readonly scrollMargin = '';
	readonly thresholds: readonly number[] = [];
	private readonly callback: IntersectionObserverCallback;

	constructor(callback: IntersectionObserverCallback) {
		this.callback = callback;
	}

	observe = (target: Element) => {
		this.callback([{ target, isIntersecting: true } as IntersectionObserverEntry], this as IntersectionObserver);
	};
	unobserve = vi.fn();
	disconnect = vi.fn();
	takeRecords = vi.fn(() => []);
}

// Assigned rather than stubbed: every test's stubs are dropped after it,
// and this would go with them.
globalThis.IntersectionObserver = ImmediateIntersectionObserver as unknown as typeof IntersectionObserver;

if (!Element.prototype.scrollIntoView) {
	Element.prototype.scrollIntoView = vi.fn();
}

/** Never reports: jsdom has no layout, so nothing it watches ever changes size. */
class SilentResizeObserver implements ResizeObserver {
	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
}

globalThis.ResizeObserver = SilentResizeObserver as unknown as typeof ResizeObserver;
