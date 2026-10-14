import { describe, it, expect } from 'vitest';

// Every source of the page as it is written, by where it is from here
const sources: Record<string, string> = import.meta.glob('../src/**/*.{ts,svelte}', {
	query: '?raw',
	import: 'default',
	eager: true
});

// What one of a pair is written as: a text in quotes or in backticks, or a name
const WORDS = String.raw`('[^']*'|"[^"]*"|\x60[^\x60]*\x60|[\w$.]+)`;
// A pair as a source writes it: `one` and `many` side by side, whichever comes first
const ONE_THEN_MANY = new RegExp(String.raw`\bone:\s*${WORDS}\s*,\s*many:\s*${WORDS}`, 'g');
const MANY_THEN_ONE = new RegExp(String.raw`\bmany:\s*${WORDS}\s*,\s*one:\s*${WORDS}`, 'g');
// A text with the quotes or backticks it is written in, and the text alone
const IN_QUOTES = /^(['"\x60])(.*)\1$/s;
const THE_TEXT_ALONE = '$2';
// The pair files are counted by, as the test names a pair, and the one source that writes it
const FILES = 'file / files';
const SHARED_WORDS = '../src/lib/utils/words.ts';

/** A pair as it is written somewhere: the singular and the plural, and the source that writes them. */
interface Written {
	pair: string;
	path: string;
}

/** A pair by what it says, whichever quotes it is written in. */
function pairOf(one: string, many: string): string {
	return [one, many].map((words) => words.replace(IN_QUOTES, THE_TEXT_ALONE)).join(' / ');
}

const written: Written[] = Object.entries(sources).flatMap(([path, text]) => [
	...[...text.matchAll(ONE_THEN_MANY)].map(([, one, many]) => ({ pair: pairOf(one, many), path })),
	...[...text.matchAll(MANY_THEN_ONE)].map(([, many, one]) => ({ pair: pairOf(one, many), path }))
]);
const byPair = Map.groupBy(written, ({ pair }) => pair);
// Where each pair is written, and where it would be were it written once: at the first of those places
const placesOf = Object.fromEntries([...byPair].map(([pair, places]) => [pair, places.map(({ path }) => path)]));
const onePlaceOf = Object.fromEntries([...byPair].map(([pair, [first]]) => [pair, [first.path]]));

/**
 * Shared code is written once, once it has a second user. A review found
 * one pair of counted words in five places, and the next pair written twice
 * would have been found by a review again: so the sources are asked.
 */
describe('a pair of counted words, the singular and the plural', () => {
	it('is written once on the page: what two places count by stands in utils/words.ts for both', () => {
		expect(placesOf).toEqual(onePlaceOf);
	});

	it('is found where it is written: files are counted by the words of utils/words.ts alone', () => {
		expect(placesOf[FILES]).toEqual([SHARED_WORDS]);
	});
});
