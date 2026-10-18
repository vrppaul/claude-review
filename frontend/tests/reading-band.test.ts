import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { FileSections } from '$lib/dom/file-sections';
import { Jumps } from '$lib/dom/jump';
import { frames } from './frames';

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

describe('a step of the keyboard to the next line', () => {
	it('goes nowhere while no reading area is watched: no line is drawn outside one', () => {
		const holdsTheKeyboard = document.body.appendChild(document.createElement('button'));
		holdsTheKeyboard.focus();

		sections.stepLine(1);

		expect(document.activeElement).toBe(holdsTheKeyboard);
	});
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

	it('is the file a jump took the reader to, though the band says the file above crosses it each time the page scrolls there', async () => {
		const first = section('a.py');
		const last = section('b.py');
		const watched = band();
		watched.report([first]);
		// A file at the end, which cannot scroll up as far as the band: each scroll to it leaves the file
		// above across the band, and the band says so once the browser has laid that scroll out
		last.scrollIntoView = () => setTimeout(() => watched.report([first]));

		sections.scrollTo('b.py');
		await frames();

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
		await frames();

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
		await frames();

		watched.report([second], [first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('is not a file taken back while it stood on the page, though the browser says afterwards that it crossed the band', () => {
		const stillOnThePage = drawn();
		const takeBack = sections.register('a.py', 'a.py', stillOnThePage);
		const watched = band();

		takeBack();
		watched.report([stillOnThePage]);

		expect(sections.fileInView).toBeNull();
	});

	it('is the band’s to say at once when the file a jump took the reader to is taken back, before they have come to rest', () => {
		const first = section('a.py');
		const takeBackTheSecond = sections.register('b.py', 'b.py', drawn());
		const watched = band();
		watched.report([first]);
		sections.scrollTo('b.py');

		takeBackTheSecond();

		expect(sections.fileInView).toBe('a.py');
	});

	it('is none once the reading area is watched no longer, though a jump took the reader to a file', () => {
		section('a.py');
		const stop = sections.watchInView(document.body);
		sections.scrollTo('a.py');

		stop();

		expect(sections.fileInView).toBeNull();
	});

	it('is still the file a jump took the reader to, when the area watched before this one is let go of after that', () => {
		section('a.py');
		const stopTheFirst = sections.watchInView(document.body);
		sections.watchInView(document.body);
		sections.scrollTo('a.py');

		stopTheFirst();

		expect(sections.fileInView).toBe('a.py');
	});

	it('leaves out a section that touches the band by less than a pixel', () => {
		band();

		expect(ReportedObserver.latest?.options.rootMargin).toBe('-1px 0px -85% 0px');
	});
});
