import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { FileSections } from '$lib/dom/file-sections';

// Enough frames for the settling watch, which looks once a frame until
// nothing has moved for two of them
const FRAMES_TO_SETTLE = 6;

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

function section(path: string): HTMLElement {
	const element = document.createElement('div');
	element.scrollIntoView = () => undefined;
	element.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
	document.body.append(element);
	sections.register(path, element);
	return element;
}

/** The observer watching the band, once the reading area is watched. */
function band(): ReportedObserver {
	sections.watchInView(document.body);
	const observer = ReportedObserver.latest;
	if (!observer) throw new Error('The band is not watched');
	return observer;
}

async function frames(count = FRAMES_TO_SETTLE): Promise<void> {
	for (let frame = 0; frame < count; frame += 1) {
		await new Promise((resolve) => requestAnimationFrame(resolve));
	}
}

beforeEach(() => {
	document.body.innerHTML = '';
	observedBefore = globalThis.IntersectionObserver;
	globalThis.IntersectionObserver = ReportedObserver as unknown as typeof IntersectionObserver;
	sections = new FileSections();
});

afterEach(() => {
	globalThis.IntersectionObserver = observedBefore;
});

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

		sections.scrollToFile('b.py');
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
		sections.scrollToFile('c.py');
		await frames();

		watched.report([second], [first]);

		expect(sections.fileInView).toBe('b.py');
	});

	it('leaves out a section that touches the band by less than a pixel', () => {
		band();

		expect(ReportedObserver.latest?.options.rootMargin).toBe('-1px 0px -85% 0px');
	});
});
