import { describe, it, expect, beforeEach, vi } from 'vitest';
import { FileSections, FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';

let sections: FileSections;

beforeEach(() => {
	sections = new FileSections();
});

// Enough frames for the settling watch, which looks once a frame until
// nothing has moved for two of them
const FRAMES_TO_SETTLE = 6;
// A moment into a scroll that is still on its way
const FRAMES_WHILE_MOVING = 2;
// Long after anything asked for has had time to be drawn, in milliseconds
const A_MINUTE = 60_000;

/** Let the settling watch run. */
async function frames(count = FRAMES_TO_SETTLE): Promise<void> {
	for (let frame = 0; frame < count; frame += 1) {
		await new Promise((resolve) => requestAnimationFrame(resolve));
	}
}

function isMarked(section: HTMLElement): boolean {
	return section.hasAttribute('data-marked');
}

function section(path: string): HTMLElement {
	const element = document.createElement('div');
	document.body.append(element);
	sections.register(path, element);
	return element;
}

// Where each file stands is invented here, jsdom laying nothing out: no
// browser test yet holds a shown file marked once a real scroll stops
describe('being taken to a file somebody else pointed at', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('does not mark the file until the scroll has stopped', async () => {
		const moving = section('a.py');
		let top = 900;
		moving.getBoundingClientRect = () => ({ top }) as DOMRect;

		sections.showFile('a.py');
		await frames(FRAMES_WHILE_MOVING);
		expect(isMarked(moving)).toBe(false);

		top = 0;
		await frames();
		expect(isMarked(moving)).toBe(true);
	});

	it('marks the file again when it is shown twice running', async () => {
		const shown = section('a.py');
		shown.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.showFile('a.py');
		await frames();
		expect(isMarked(shown)).toBe(true);

		sections.showFile('a.py');
		expect(isMarked(shown)).toBe(false);
		await frames();
		expect(isMarked(shown)).toBe(true);
	});

	it('marks only the file asked for last', async () => {
		const first = section('a.py');
		const second = section('b.py');
		first.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
		second.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.showFile('a.py');
		sections.showFile('b.py');
		await frames();

		expect(isMarked(first)).toBe(false);
		expect(isMarked(second)).toBe(true);
	});

	it('says nothing about a file the review does not hold', () => {
		expect(() => sections.showFile('missing.py')).not.toThrow();
	});
});

describe('being taken to a thread', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('brings a thread already drawn into view', () => {
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();
		sections.registerThread('comment-1', thread);

		sections.goToThread('comment-1', 'a.py');

		expect(thread.scrollIntoView).toHaveBeenCalled();
	});

	it('goes to the file of a thread not yet drawn, and to the thread once it is', () => {
		const file = section('a.py');
		file.scrollIntoView = vi.fn();
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();

		sections.goToThread('comment-1', 'a.py');
		expect(file.scrollIntoView).toHaveBeenCalled();
		expect(thread.scrollIntoView).not.toHaveBeenCalled();

		sections.registerThread('comment-1', thread);

		expect(thread.scrollIntoView).toHaveBeenCalled();
	});

	it('does not go to a thread drawn long after it was asked for', () => {
		const later = document.createElement('div');
		later.scrollIntoView = vi.fn();
		const clock = vi.spyOn(performance, 'now').mockReturnValue(0);
		sections.goToThread('comment-1', 'a.py');

		clock.mockReturnValue(A_MINUTE);
		sections.registerThread('comment-1', later);

		expect(later.scrollIntoView).not.toHaveBeenCalled();
		clock.mockRestore();
	});

	it('does not go to a thread drawn later once the reader has asked for another', () => {
		const first = document.createElement('div');
		first.scrollIntoView = vi.fn();
		sections.goToThread('comment-1', 'a.py');
		sections.goToThread('comment-2', 'a.py');

		sections.registerThread('comment-1', first);

		expect(first.scrollIntoView).not.toHaveBeenCalled();
	});
});

describe('moving the reader', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	/** A system that has, or has not, asked for less motion. */
	function lessMotion(asked: boolean) {
		vi.stubGlobal(
			'matchMedia',
			vi.fn().mockImplementation((query: string) => ({ matches: asked && query.includes('reduced-motion') }))
		);
	}

	it('glides to a file and to a thread', () => {
		lessMotion(false);
		const file = section('a.py');
		file.scrollIntoView = vi.fn();
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();
		sections.registerThread('comment-1', thread);

		sections.showFile('a.py');
		sections.goToThread('comment-1', 'a.py');

		expect(file.scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'smooth' }));
		expect(thread.scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'smooth' }));
	});

	it('goes there at once for a reader who asked their system for less motion', () => {
		lessMotion(true);
		const file = section('a.py');
		file.scrollIntoView = vi.fn();
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();
		sections.registerThread('comment-1', thread);

		sections.showFile('a.py');
		sections.goToThread('comment-1', 'a.py');

		expect(file.scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'instant' }));
		expect(thread.scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ behavior: 'instant' }));
	});
});

// The band here sees every section crossing it (setup.ts's observer); which
// file a real scroll puts there is held in the browser by
// tests/e2e/test_keys_and_focus.py::test_v_after_a_jump_from_the_tree_marks_the_file_jumped_to
describe('knowing which file the reader is in', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('is the file holding the focus', () => {
		section('a.py');
		const reading = section('b.py');
		const lineNumber = document.createElement('button');
		reading.append(lineNumber);

		lineNumber.focus();

		expect(sections.focused()).toBe('b.py');
	});

	it('is none while the focus is outside every file', () => {
		section('a.py');

		expect(sections.focused()).toBeNull();
	});

	it('is none while the reading area is not watched', () => {
		section('a.py');

		expect(sections.fileInView).toBeNull();
	});

	it('is the earliest file in the reading band, in the order the page draws them', () => {
		const first = document.createElement('div');
		const second = document.createElement('div');
		document.body.append(first, second);
		sections.register('b.py', second);
		sections.register('a.py', first);

		sections.watchInView(document.body);

		expect(sections.fileInView).toBe('a.py');
	});

	it('follows a file drawn after the watching began', () => {
		sections.watchInView(document.body);

		section('a.py');

		expect(sections.fileInView).toBe('a.py');
	});

	it('moves on to the next file in the band when the one in view is taken away', () => {
		const leaving = document.createElement('div');
		document.body.append(leaving);
		const takeBack = sections.register('a.py', leaving);
		section('b.py');
		sections.watchInView(document.body);

		takeBack();

		expect(sections.fileInView).toBe('b.py');
	});
});

describe('what stands for a line where it is not drawn', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	/** A file's section with its fold toggle, on the page in the order made, said to the sections in another. */
	function sectionWithToggle(): { element: HTMLElement; toggle: HTMLElement } {
		const element = document.createElement('div');
		const toggle = document.createElement('button');
		toggle.dataset.role = FOLD_TOGGLE_ROLE;
		element.append(toggle);
		document.body.append(element);
		return { element, toggle };
	}

	it('is the toggle of the first file on the page for a file the diff does not hold, whichever was drawn first', () => {
		const first = sectionWithToggle();
		const second = sectionWithToggle();
		sections.register('b.py', second.element);
		sections.register('a.py', first.element);

		expect(sections.lineOrFile('reverted.py', 'new:1')).toBe(first.toggle);
	});

	it("is the file's own toggle for a line of it that is not drawn", () => {
		const first = sectionWithToggle();
		const second = sectionWithToggle();
		sections.register('a.py', first.element);
		sections.register('b.py', second.element);

		expect(sections.lineOrFile('b.py', 'new:9')).toBe(second.toggle);
	});
});
