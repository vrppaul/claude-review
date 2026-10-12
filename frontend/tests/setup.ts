/** jsdom implements none of these; components under test rely on them. */
import { afterEach, beforeEach, onTestFinished, vi } from 'vitest';
import { failOnUnanswered } from './fake-server';
import { leavePage } from './review';

// Every test starts from a page opened fresh: each builds its own review,
// and what one test leaves in storage, or in the draft the page holds,
// would otherwise be the next test's starting point
beforeEach(() => {
	leavePage();
	localStorage.clear();
	// A page that asked its server a route the test never said how to answer
	// ran a failure path nobody meant to test. Said once the test is over and
	// tidied away, so the next test does not start in what it left.
	onTestFinished(failOnUnanswered);
});

// Every test ends with its page gone, as it starts: a review left open would
// keep its draft a moment later, after the test, and the file, are over.
// And a test that switched to fake timers and failed before switching back
// would leave the next one on them: every test ends on the real clock
afterEach(() => {
	leavePage();
	vi.useRealTimers();
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

/**
 * jsdom has dialogs but cannot show or close one. This stand-in opens it,
 * puts the keyboard on the first thing in it that takes it, and closes it
 * once, saying so. It is not a browser's modal, and leaves out:
 * - the close event a moment later: it is said at once, inside close();
 * - the keyboard given back, on closing, to what had it before;
 * - Escape, which a browser answers by cancelling and closing the dialog;
 * - the keyboard held inside, and the page under it inert.
 * The browser tests hold those: tests/e2e/test_keys_and_focus.py and the
 * keys list's tests in tests/e2e/test_review_flow.py.
 */
HTMLDialogElement.prototype.showModal ??= function showModal(this: HTMLDialogElement) {
	this.open = true;
	this.querySelector<HTMLElement>('button, [href], input, select, textarea, [tabindex]')?.focus();
};
HTMLDialogElement.prototype.close ??= function close(this: HTMLDialogElement) {
	// A dialog already closed says nothing more, as in a browser
	if (!this.open) return;
	this.open = false;
	this.dispatchEvent(new Event('close'));
};
