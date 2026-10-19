import { beforeEach, describe, expect, it } from 'vitest';
import { BuiltWhenNear } from '$lib/dom/built-when-near.svelte';
import { scriptTheScroll, scrollTo } from './scripted-scroll';

describe('what is built when the reader comes near it', () => {
	let element: HTMLElement;

	beforeEach(() => {
		scriptTheScroll();
		element = document.createElement('div');
	});

	it('is not built while the reader is elsewhere', () => {
		const nearness = new BuiltWhenNear();
		nearness.watch(element, null);

		scrollTo();

		expect(nearness.built).toBe(false);
	});

	it('is built once the reader comes near it', () => {
		const nearness = new BuiltWhenNear();
		nearness.watch(element, null);

		scrollTo(element);

		expect(nearness.built).toBe(true);
	});
});
