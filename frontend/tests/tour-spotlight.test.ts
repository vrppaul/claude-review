import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import TourSpotlight from '$lib/components/TourSpotlight.svelte';

/** A lit element whose place on the page the test decides. */
function placeAt(name: string, rect: { left: number; top: number; width: number; height: number }) {
	const element = document.createElement('div');
	element.dataset.tour = name;
	element.getBoundingClientRect = () =>
		({ ...rect, right: rect.left + rect.width, bottom: rect.top + rect.height }) as DOMRect;
	document.body.append(element);
	return element;
}

async function nextFrame() {
	await new Promise((resolve) => requestAnimationFrame(resolve));
	await tick();
}

describe('the light over a tour step', () => {
	afterEach(() => {
		document.body.innerHTML = '';
		vi.restoreAllMocks();
	});

	it('follows what it lights without setting itself up again on every move', async () => {
		const lit = placeAt('file-tree', { left: 10, top: 20, width: 100, height: 50 });
		const listening = vi.spyOn(window, 'addEventListener');
		const { getByTestId } = render(TourSpotlight, { props: { targets: ['file-tree'] } });
		await tick();
		const setUps = listening.mock.calls.filter(([type]) => type === 'scroll').length;

		lit.getBoundingClientRect = () =>
			({ left: 10, top: 80, width: 100, height: 50, right: 110, bottom: 130 }) as DOMRect;
		window.dispatchEvent(new Event('scroll'));
		await nextFrame();

		expect(getByTestId('tour-spotlight').style.top).toBe('76px');
		expect(listening.mock.calls.filter(([type]) => type === 'scroll').length).toBe(setUps);
	});

	it('watches the size of what it lights, which grows as a comment is typed', async () => {
		const lit = placeAt('comment-field', { left: 0, top: 0, width: 300, height: 80 });
		const watched: Element[] = [];
		const silent = globalThis.ResizeObserver;
		globalThis.ResizeObserver = class {
			observe = (element: Element) => watched.push(element);
			unobserve = vi.fn();
			disconnect = vi.fn();
		} as unknown as typeof ResizeObserver;

		render(TourSpotlight, { props: { targets: ['comment-field'] } });
		await tick();
		globalThis.ResizeObserver = silent;

		expect(watched).toContain(lit);
	});
});
