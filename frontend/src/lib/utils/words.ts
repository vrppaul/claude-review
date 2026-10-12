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

/** A count and the words that go with it: the singular for one, the plural for none and for many. */
export function counted(count: number, one: string, many: string): string {
	return `${count} ${count === 1 ? one : many}`;
}
