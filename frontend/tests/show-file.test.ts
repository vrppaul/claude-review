import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { registerSection, showFile } from '$lib/utils/scroll';

/** Let the settling watch run: it looks once a frame until nothing moves. */
async function frames(count = 6): Promise<void> {
	for (let i = 0; i < count; i += 1) {
		await new Promise((resolve) => requestAnimationFrame(resolve));
	}
}

function section(path: string): HTMLElement {
	const element = document.createElement('div');
	document.body.append(element);
	registerSection(path, element);
	return element;
}

describe('being taken to a file somebody else pointed at', () => {
	beforeEach(() => {
		vi.stubGlobal('scrollIntoView', vi.fn());
		Element.prototype.scrollIntoView = vi.fn();
		document.body.innerHTML = '';
	});

	afterEach(() => {
		vi.unstubAllGlobals();
		vi.useRealTimers();
	});

	it('does not mark the file until the scroll has stopped', async () => {
		const moving = section('a.py');
		let top = 900;
		moving.getBoundingClientRect = () => ({ top }) as DOMRect;

		showFile('a.py');
		await frames(2);
		expect(moving.classList.contains('cr-marked')).toBe(false);

		top = 0;
		await frames();
		expect(moving.classList.contains('cr-marked')).toBe(true);
	});

	it('marks the file again when it is shown twice running', async () => {
		const shown = section('a.py');
		shown.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		showFile('a.py');
		await frames();
		expect(shown.classList.contains('cr-marked')).toBe(true);

		showFile('a.py');
		expect(shown.classList.contains('cr-marked')).toBe(false);
		await frames();
		expect(shown.classList.contains('cr-marked')).toBe(true);
	});

	it('marks only the file asked for last', async () => {
		const first = section('a.py');
		const second = section('b.py');
		first.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;
		second.getBoundingClientRect = () => ({ top: 0 }) as DOMRect;

		showFile('a.py');
		showFile('b.py');
		await frames();

		expect(first.classList.contains('cr-marked')).toBe(false);
		expect(second.classList.contains('cr-marked')).toBe(true);
	});

	it('says nothing about a file the review does not hold', () => {
		expect(() => showFile('missing.py')).not.toThrow();
	});
});
