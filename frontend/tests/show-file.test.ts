import { describe, it, expect, beforeEach, vi } from 'vitest';
import { FileSections, FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
import { Jumps } from '$lib/dom/jump';
import { frames, FRAMES_TO_SETTLE, untilAGlideWouldHaveBegun } from './frames';

let sections: FileSections;

beforeEach(() => {
	sections = new FileSections(new Jumps());
});

// Enough for a jump that came to rest, was scrolled on from there, and came to rest where it was sent
const FRAMES_TO_SETTLE_TWICE = FRAMES_TO_SETTLE * 2;
// Where a section's head stands on screen, in pixels below the top of its area: at the top, where a
// jump sends it; pushed down from there by what was built above it; and where a reader's scroll left it
const AT_THE_TOP = 0;
const PUSHED_DOWN = 300;
const WHERE_THE_READER_WENT = 500;
// And scrolled off it, above the area, by going to a thread far down the section
const OFF_THE_TOP = -400;
// What a reader does to move themselves, or to act where they are
const READERS_OWN_MOVES = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
// A moment into a scroll that is still on its way
const FRAMES_WHILE_MOVING = 2;
// Long after anything asked for has had time to be drawn, or to come to rest, in milliseconds
const A_MINUTE = 60_000;

function isMarked(section: HTMLElement): boolean {
	return section.hasAttribute('data-marked');
}

function section(path: string): HTMLElement {
	const element = document.createElement('div');
	document.body.append(element);
	sections.register(path, path, element);
	return element;
}

/** Where an element stands on screen, as a test says: jsdom lays nothing out. */
interface Standing {
	top: number;
}

/**
 * Give an element a place on screen that a test moves it from: scrolling to
 * it puts it where the scroll sends it, and it says where it stands now.
 */
function placed(element: HTMLElement, sentTo: number): Standing {
	const standing = { top: sentTo };
	element.getBoundingClientRect = () => ({ top: standing.top }) as DOMRect;
	element.scrollIntoView = () => (standing.top = sentTo);
	return standing;
}

// Where each file stands is invented here, jsdom laying nothing out: where a
// real scroll leaves a file, and that it is marked there, is held in the
// browser by tests/e2e/test_jumps.py
describe('being taken to a file somebody else pointed at', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('does not mark the file until the scroll has stopped', async () => {
		const moving = section('a.py');
		let top = 900;
		moving.getBoundingClientRect = () => ({ top }) as DOMRect;

		sections.show('a.py');
		await frames(FRAMES_WHILE_MOVING);
		expect(isMarked(moving)).toBe(false);

		top = 0;
		await frames();
		expect(isMarked(moving)).toBe(true);
	});

	it('does not mark a file that stands still before the glide to it has begun: a glide takes a few frames to begin', async () => {
		const yetToMove = section('a.py');
		yetToMove.getBoundingClientRect = () => ({ top: 900 }) as DOMRect;

		sections.show('a.py');
		await frames();

		expect(isMarked(yetToMove)).toBe(false);
	});

	it('marks a file that stands where it is sent already, once a glide would have begun', async () => {
		const shown = section('a.py');
		shown.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.show('a.py');
		await untilAGlideWouldHaveBegun();

		expect(isMarked(shown)).toBe(true);
	});

	it('marks the file again when it is shown twice running', async () => {
		const shown = section('a.py');
		shown.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.show('a.py');
		await untilAGlideWouldHaveBegun();
		expect(isMarked(shown)).toBe(true);

		sections.show('a.py');
		expect(isMarked(shown)).toBe(false);
		await untilAGlideWouldHaveBegun();
		expect(isMarked(shown)).toBe(true);
	});

	it('marks only the file asked for last', async () => {
		const first = section('a.py');
		const second = section('b.py');
		first.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
		second.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.show('a.py');
		sections.show('b.py');
		await untilAGlideWouldHaveBegun();

		expect(isMarked(first)).toBe(false);
		expect(isMarked(second)).toBe(true);
	});

	it('marks a file that never comes to rest all the same, once it has been waited on long enough', async () => {
		const restless = section('a.py');
		let top = 0;
		// Wherever it is looked at, it has moved on from where it was
		restless.getBoundingClientRect = () => ({ top: (top += 1) }) as DOMRect;
		const clock = vi.spyOn(performance, 'now').mockReturnValue(0);

		sections.show('a.py');
		await frames();
		expect(isMarked(restless)).toBe(false);

		clock.mockReturnValue(A_MINUTE);
		await frames();
		expect(isMarked(restless)).toBe(true);
	});

	it('says nothing about a file the review does not hold', () => {
		expect(() => sections.show('missing.py')).not.toThrow();
	});

	it('is brought back to where it was sent when the files built on the way pushed it from there, and marked there', async () => {
		const shown = section('a.py');
		const standing = placed(shown, AT_THE_TOP);

		sections.show('a.py');
		standing.top = PUSHED_DOWN;
		await frames(FRAMES_TO_SETTLE_TWICE);

		expect(standing.top).toBe(AT_THE_TOP);
		expect(isMarked(shown)).toBe(true);
	});

	it.each(READERS_OWN_MOVES)(
		'is left where the reader went meanwhile, and marked there: after a %s of theirs',
		async (move) => {
			const shown = section('a.py');
			const standing = placed(shown, AT_THE_TOP);

			sections.show('a.py');
			window.dispatchEvent(new Event(move));
			standing.top = WHERE_THE_READER_WENT;
			await frames(FRAMES_TO_SETTLE_TWICE);

			expect(standing.top).toBe(WHERE_THE_READER_WENT);
			expect(isMarked(shown)).toBe(true);
		}
	);
});

describe('being taken to a section', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('is brought back to the top when what was built around it pushed it from there', async () => {
		const standing = placed(section('a.py'), AT_THE_TOP);

		sections.scrollTo('a.py');
		standing.top = PUSHED_DOWN;
		await frames(FRAMES_TO_SETTLE_TWICE);

		expect(standing.top).toBe(AT_THE_TOP);
	});

	it('leaves nothing listening for the reader’s moves once it has come to rest', async () => {
		const listening = vi.spyOn(window, 'addEventListener');
		placed(section('a.py'), AT_THE_TOP);

		sections.scrollTo('a.py');
		await frames();

		// Each move was listened for until a signal said to stop: the only trace a listener leaves on the page
		const stopped = listening.mock.calls.map(([, , until]) => until.signal.aborted);
		expect(stopped).toEqual(READERS_OWN_MOVES.map(() => true));
	});

	it('is not gone back to once the reader is taken to another', async () => {
		const first = placed(section('a.py'), AT_THE_TOP);
		placed(section('b.py'), AT_THE_TOP);

		sections.scrollTo('a.py');
		sections.scrollTo('b.py');
		first.top = PUSHED_DOWN;
		await frames(FRAMES_TO_SETTLE_TWICE);

		expect(first.top).toBe(PUSHED_DOWN);
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

	it('stays on a thread once it is drawn: its file is not brought back to the top from under it', async () => {
		const file = placed(section('a.py'), AT_THE_TOP);
		const thread = document.createElement('div');
		// Going to a thread far down its file scrolls the file's head off the top
		thread.scrollIntoView = () => (file.top = OFF_THE_TOP);

		sections.goToThread('comment-1', 'a.py');
		sections.registerThread('comment-1', thread);
		await frames(FRAMES_TO_SETTLE_TWICE);

		expect(file.top).toBe(OFF_THE_TOP);
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

	it('glides a file’s head to the top of its area, and a thread to the middle', () => {
		lessMotion(false);
		const file = section('a.py');
		file.scrollIntoView = vi.fn();
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();
		sections.registerThread('comment-1', thread);

		sections.show('a.py');
		sections.goToThread('comment-1', 'a.py');

		expect(file.scrollIntoView).toHaveBeenCalledWith({ block: 'start', behavior: 'smooth' });
		expect(thread.scrollIntoView).toHaveBeenCalledWith({ block: 'center', behavior: 'smooth' });
	});

	it('puts them there at once for a reader who asked their system for less motion', () => {
		lessMotion(true);
		const file = section('a.py');
		file.scrollIntoView = vi.fn();
		const thread = document.createElement('div');
		thread.scrollIntoView = vi.fn();
		sections.registerThread('comment-1', thread);

		sections.show('a.py');
		sections.goToThread('comment-1', 'a.py');

		expect(file.scrollIntoView).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
		expect(thread.scrollIntoView).toHaveBeenCalledWith({ block: 'center', behavior: 'instant' });
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

		expect(sections.currentFile()).toBe('b.py');
	});

	it('is none while the focus is outside every file', () => {
		section('a.py');

		expect(sections.currentFile()).toBeNull();
	});

	it('is none while the reading area is not watched', () => {
		section('a.py');

		expect(sections.fileInView).toBeNull();
	});

	it('is the earliest file in the reading band, in the order the page draws them', () => {
		const first = document.createElement('div');
		const second = document.createElement('div');
		document.body.append(first, second);
		sections.register('b.py', 'b.py', second);
		sections.register('a.py', 'a.py', first);

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
		const takeBack = sections.register('a.py', 'a.py', leaving);
		section('b.py');
		sections.watchInView(document.body);

		takeBack();

		expect(sections.fileInView).toBe('b.py');
	});
});

describe('a file drawn in several pieces, as a story draws one', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	/** A piece of a file on the page, known by a key of its own. */
	function piece(key: string, path: string): HTMLElement {
		const element = document.createElement('div');
		element.scrollIntoView = vi.fn();
		document.body.append(element);
		sections.register(key, path, element);
		return element;
	}

	/** A line's number drawn in a piece, known by its place. */
	function lineIn(drawn: HTMLElement, place: string): HTMLElement {
		const number = document.createElement('button');
		number.dataset.place = place;
		drawn.append(number);
		return number;
	}

	it('finds a line in whichever piece of its file draws it', () => {
		lineIn(piece('step-1', 'a.py'), 'new:3');
		const further = lineIn(piece('step-2', 'a.py'), 'new:40');

		expect(sections.lineOrFile('a.py', 'new:40')).toBe(further);
	});

	it('names the file of the piece being read', () => {
		piece('step-1', 'a.py');

		sections.watchInView(document.body);

		expect(sections.fileInView).toBe('a.py');
	});

	it('says which piece the reader is in by its own key', () => {
		lineIn(piece('step-1', 'a.py'), 'new:3');
		const further = lineIn(piece('step-2', 'a.py'), 'new:40');

		further.focus();

		expect(sections.current()).toBe('step-2');
	});

	it('goes to the piece a thread will be drawn in, not to the first piece of its file', () => {
		const first = piece('step-1', 'a.py');
		const further = piece('step-2', 'a.py');

		sections.goToThread('comment-1', 'step-2');

		expect(further.scrollIntoView).toHaveBeenCalled();
		expect(first.scrollIntoView).not.toHaveBeenCalled();
	});

	it('goes on finding a line of the file when another piece of it is taken away', () => {
		const leaving = document.createElement('div');
		document.body.append(leaving);
		const takeBack = sections.register('step-1', 'a.py', leaving);
		const staying = lineIn(piece('step-2', 'a.py'), 'new:40');

		takeBack();

		expect(sections.lineOrFile('a.py', 'new:40')).toBe(staying);
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
		sections.register('b.py', 'b.py', second.element);
		sections.register('a.py', 'a.py', first.element);

		expect(sections.lineOrFile('reverted.py', 'new:1')).toBe(first.toggle);
	});

	it("is the file's own toggle for a line of it that is not drawn", () => {
		const first = sectionWithToggle();
		const second = sectionWithToggle();
		sections.register('a.py', 'a.py', first.element);
		sections.register('b.py', 'b.py', second.element);

		expect(sections.lineOrFile('b.py', 'new:9')).toBe(second.toggle);
	});
});

// A view just brought on screen has drawn nothing yet: what the reader was
// being taken to in it is asked for first, and announces itself a moment later
describe('a section asked for before it is drawn', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	/** Something on the page that has not announced itself yet, and says when it is brought into view. */
	function notYetDrawn(): HTMLElement {
		const element = document.createElement('div');
		element.scrollIntoView = vi.fn();
		document.body.append(element);
		return element;
	}

	it('is gone to once it is drawn', () => {
		const late = notYetDrawn();

		sections.scrollTo('a.py');
		sections.register('a.py', 'a.py', late);

		expect(late.scrollIntoView).toHaveBeenCalled();
	});

	it('is shown and marked once it is drawn, where somebody else pointed at it', async () => {
		const late = notYetDrawn();
		late.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		sections.show('a.py');
		sections.register('a.py', 'a.py', late);
		await untilAGlideWouldHaveBegun();

		expect(late.scrollIntoView).toHaveBeenCalled();
		expect(isMarked(late)).toBe(true);
	});

	it('is not gone to when it is drawn long after it was asked for', () => {
		const late = notYetDrawn();
		const clock = vi.spyOn(performance, 'now').mockReturnValue(0);
		sections.scrollTo('a.py');

		clock.mockReturnValue(A_MINUTE);
		sections.register('a.py', 'a.py', late);

		expect(late.scrollIntoView).not.toHaveBeenCalled();
		clock.mockRestore();
	});

	it('is not gone to once the reader has gone somewhere else', () => {
		const elsewhere = section('b.py');
		elsewhere.scrollIntoView = vi.fn();
		const late = notYetDrawn();

		sections.scrollTo('a.py');
		sections.scrollTo('b.py');
		sections.register('a.py', 'a.py', late);

		expect(late.scrollIntoView).not.toHaveBeenCalled();
	});

	it('is the one gone to, not another section drawn meanwhile', () => {
		const another = notYetDrawn();

		sections.scrollTo('a.py');
		sections.register('b.py', 'b.py', another);

		expect(another.scrollIntoView).not.toHaveBeenCalled();
	});

	it('is gone to once, not again when it is drawn anew', () => {
		const late = notYetDrawn();
		const drawnAnew = notYetDrawn();

		sections.scrollTo('a.py');
		sections.register('a.py', 'a.py', late);
		sections.register('a.py', 'a.py', drawnAnew);

		expect(drawnAnew.scrollIntoView).not.toHaveBeenCalled();
	});

	it('is no longer the way to a thread once the reader is shown another section', () => {
		const shown = section('b.py');
		shown.scrollIntoView = vi.fn();
		const thread = notYetDrawn();

		sections.goToThread('comment-1', 'a.py');
		sections.show('b.py');
		sections.registerThread('comment-1', thread);

		expect(thread.scrollIntoView).not.toHaveBeenCalled();
	});

	it('takes the reader on to the thread asked for in it, once the thread is drawn too', () => {
		const late = notYetDrawn();
		const thread = notYetDrawn();

		sections.goToThread('comment-1', 'a.py');
		sections.register('a.py', 'a.py', late);
		expect(late.scrollIntoView).toHaveBeenCalled();
		expect(thread.scrollIntoView).not.toHaveBeenCalled();

		sections.registerThread('comment-1', thread);

		expect(thread.scrollIntoView).toHaveBeenCalled();
	});

	it('does not pull the screen off a thread that was drawn before it', () => {
		const late = notYetDrawn();
		const thread = notYetDrawn();

		sections.goToThread('comment-1', 'a.py');
		sections.registerThread('comment-1', thread);
		sections.register('a.py', 'a.py', late);

		expect(late.scrollIntoView).not.toHaveBeenCalled();
	});
});
