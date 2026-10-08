import { describe, it, expect, beforeEach } from 'vitest';
import { registerSection, showFile } from '$lib/utils/scroll';

// Enough frames for the settling watch, which looks once a frame until
// nothing has moved for two of them
const FRAMES_TO_SETTLE = 6;
// A moment into a scroll that is still on its way
const FRAMES_WHILE_MOVING = 2;

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
	registerSection(path, element);
	return element;
}

describe('being taken to a file somebody else pointed at', () => {
	beforeEach(() => {
		document.body.innerHTML = '';
	});

	it('does not mark the file until the scroll has stopped', async () => {
		const moving = section('a.py');
		let top = 900;
		moving.getBoundingClientRect = () => ({ top }) as DOMRect;

		showFile('a.py');
		await frames(FRAMES_WHILE_MOVING);
		expect(isMarked(moving)).toBe(false);

		top = 0;
		await frames();
		expect(isMarked(moving)).toBe(true);
	});

	it('marks the file again when it is shown twice running', async () => {
		const shown = section('a.py');
		shown.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		showFile('a.py');
		await frames();
		expect(isMarked(shown)).toBe(true);

		showFile('a.py');
		expect(isMarked(shown)).toBe(false);
		await frames();
		expect(isMarked(shown)).toBe(true);
	});

	it('marks only the file asked for last', async () => {
		const first = section('a.py');
		const second = section('b.py');
		first.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
		second.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		showFile('a.py');
		showFile('b.py');
		await frames();

		expect(isMarked(first)).toBe(false);
		expect(isMarked(second)).toBe(true);
	});

	it('says nothing about a file the review does not hold', () => {
		expect(() => showFile('missing.py')).not.toThrow();
	});
});
