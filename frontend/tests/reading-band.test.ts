import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { FileSections } from '$lib/dom/file-sections';
import { Jumps } from '$lib/dom/jump';
import { frames, untilAGlideWouldHaveBegun } from './frames';

/** An observer the test reports crossings through, as the browser would once it has laid the page out. */
class ReportedObserver {
	static latest: ReportedObserver | null = null;
	readonly options: IntersectionObserverInit;
	readonly #callback: IntersectionObserverCallback;

	constructor(callback: IntersectionObserverCallback, options: IntersectionObserverInit) {
		this.#callback = callback;
		this.options = options;
		ReportedObserver.latest = this;
	}

	observe() {}
	unobserve() {}
	disconnect() {}

	/** The browser saying which sections now cross the band, and which no longer do. */
	report(crossing: Element[], leaving: Element[] = []) {
		const entries = [
			...crossing.map((target) => ({ target, isIntersecting: true })),
			...leaving.map((target) => ({ target, isIntersecting: false }))
		] as IntersectionObserverEntry[];
		this.#callback(entries, this as unknown as IntersectionObserver);
	}
}

let sections: FileSections;
let observedBefore: typeof IntersectionObserver;

/** Something drawn on the page that stands still wherever it is scrolled to: jsdom lays nothing out. */
function drawn(): HTMLElement {
	const element = document.createElement('div');
	element.scrollIntoView = () => undefined;
	element.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
	document.body.append(element);
	return element;
}

function section(path: string): HTMLElement {
	const element = drawn();
	sections.register(path, path, element);
	return element;
}

/** The observer watching the band, once the reading area is watched. */
function band(): ReportedObserver {
	sections.watchInView(document.body);
	const observer = ReportedObserver.latest;
	if (!observer) throw new Error('The band is not watched');
	return observer;
}

beforeEach(() => {
	document.body.innerHTML = '';
	observedBefore = globalThis.IntersectionObserver;
	globalThis.IntersectionObserver = ReportedObserver as unknown as typeof IntersectionObserver;
	sections = new FileSections(new Jumps());
});

afterEach(() => {
	globalThis.IntersectionObserver = observedBefore;
});

// What crosses the band is reported by the test, not measured: the band
// over a real layout is held by
// tests/e2e/test_keys_and_focus.py::test_v_after_a_jump_from_the_tree_marks_the_file_jumped_to,
// and its one-pixel edge by no browser test, which cannot make the sub-pixel case
describe('the file being read', () => {
	it('is the one whose header is at the top: the first of those crossing the band', () => {
		const first = section('a.py');
		const second = section('b.py');

		band().report([second, first]);

		expect(sections.fileInView).toBe('a.py');
	});

	it('is the file a jump took the reader to, though the band still shows the one above it', () => {
		const first = section('a.py');
		section('b.py');
		const watched = band();
		watched.report([first]);

		sections.scrollTo('b.py');
		// The file above still touches the band as the jump lands: a short file at
		// the end cannot scroll up to it, and a fraction of a pixel is enough
		watched.report([first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('is the band’s to say again once the reader moves on from where a jump landed', async () => {
		const first = section('a.py');
		const second = section('b.py');
		section('c.py');
		const watched = band();
		watched.report([first]);
		sections.scrollTo('c.py');
		await frames();

		watched.report([second], [first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('is the band’s to say again once the reader moves on from a file somebody else showed them', async () => {
		const first = section('a.py');
		const second = section('b.py');
		section('c.py');
		const watched = band();
		watched.report([first]);
		sections.show('c.py');
		await untilAGlideWouldHaveBegun();

		watched.report([second], [first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('is the band’s to say again once the reader moves on from a thread they were taken to through its file', async () => {
		const first = section('a.py');
		const second = section('b.py');
		section('c.py');
		const watched = band();
		watched.report([first]);
		// The thread is not drawn yet: the reader is taken to its file, and on to the thread the moment
		// it is drawn, before the jump to the file has come to rest
		sections.goToThread('comment-1', 'c.py');
		sections.registerThread('comment-1', drawn());
		await untilAGlideWouldHaveBegun();

		watched.report([second], [first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('leaves out a section that touches the band by less than a pixel', () => {
		band();

		expect(ReportedObserver.latest?.options.rootMargin).toBe('-1px 0px -85% 0px');
	});
});
