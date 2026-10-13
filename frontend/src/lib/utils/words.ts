/**
 * Counts said in words, one way everywhere: "1 file", "0 files", "3 files
 * have". Each place names its own words, singular and plural; the rule for
 * which goes with a count is kept here, once.
 */

/** The words a count goes with: the singular for one, the plural for none and for many. */
export interface CountedWords {
	one: string;
	many: string;
}

/** The words that go with a count, said without it: the singular for one, the plural for none and for many. */
export function wordsFor(count: number, words: CountedWords): string {
	return count === 1 ? words.one : words.many;
}

/** A count and the words that go with it: "1 file", "0 files". */
export function counted(count: number, words: CountedWords): string {
	return `${count} ${wordsFor(count, words)}`;
}
