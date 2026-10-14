import { describe, it, expect } from 'vitest';
import { sideIsTheReviews, whyNotTheReviews } from '$lib/anchors/numbering';

describe("whose a side's line numbers are", () => {
	it("are the review's own on both sides of the review's own diff", () => {
		expect(sideIsTheReviews('old', 'the-reviews')).toBe(true);
		expect(sideIsTheReviews('new', 'the-reviews')).toBe(true);
	});

	it("are the base's on the left of a narrower base, and the review's on the right", () => {
		expect(sideIsTheReviews('old', 'a-narrower-bases')).toBe(false);
		expect(sideIsTheReviews('new', 'a-narrower-bases')).toBe(true);
	});
});

describe("why nothing is written on a line whose number is not the review's own", () => {
	it('is not said of a line whose number is', () => {
		expect(whyNotTheReviews('new', 'a-narrower-bases')).toBeNull();
	});

	it('says a removed line belongs to the narrower base on screen', () => {
		expect(whyNotTheReviews('old', 'a-narrower-bases')).toBe(
			'A removed line belongs to the base on screen. Show the whole diff to write here.'
		);
	});
});
