/** jsdom implements neither of these; components under test rely on both. */
import { vi } from 'vitest';

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
		this.callback(
			[{ target, isIntersecting: true } as IntersectionObserverEntry],
			this as IntersectionObserver
		);
	};
	unobserve = vi.fn();
	disconnect = vi.fn();
	takeRecords = vi.fn(() => []);
}

vi.stubGlobal('IntersectionObserver', ImmediateIntersectionObserver);

if (!Element.prototype.scrollIntoView) {
	Element.prototype.scrollIntoView = vi.fn();
}
