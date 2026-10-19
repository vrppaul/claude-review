import { afterEach, describe, expect, it } from 'vitest';
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

// Where the lit element stands is invented: no browser test measures the light over a real page
describe('the light over a tour step', () => {
	afterEach(() => {
		document.body.innerHTML = '';
	});

	it('follows what it lights as the page moves under it', async () => {
		const lit = placeAt('file-tree', { left: 10, top: 20, width: 100, height: 50 });
		const { getByTestId } = render(TourSpotlight, { props: { targets: ['file-tree'] } });
		await tick();

		lit.getBoundingClientRect = () =>
			({ left: 10, top: 80, width: 100, height: 50, right: 110, bottom: 130 }) as DOMRect;
		window.dispatchEvent(new Event('scroll'));
		await nextFrame();

		// Where the light stands, as the component hands it to the stylesheet
		expect(getByTestId('tour-spotlight').style.getPropertyValue('--cr-spot-top')).toBe('76px');
	});
});
