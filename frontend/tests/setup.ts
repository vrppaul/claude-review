/** jsdom implements neither of these; components under test rely on both. */
import { vi } from 'vitest';

class NoopIntersectionObserver implements IntersectionObserver {
	readonly root = null;
	readonly rootMargin = '';
	readonly thresholds: readonly number[] = [];
	readonly scrollMargin = '';
	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
	takeRecords = vi.fn(() => []);
}

vi.stubGlobal('IntersectionObserver', NoopIntersectionObserver);

if (!Element.prototype.scrollIntoView) {
	Element.prototype.scrollIntoView = vi.fn();
}
