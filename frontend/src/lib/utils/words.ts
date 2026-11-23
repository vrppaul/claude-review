/**
 * Counts said in words, one way everywhere: "1 file", "0 files", "3 files
 * have". The rule for which word goes with a count is kept here, once, and
 * so are the words more than one place counts by. A place that is alone in
 * counting something names its own, singular and plural.
 */

/** The words a count goes with: the singular for one, the plural for none and for many. */
export interface CountedWords {
	one: string;
	many: string;
}

/** What files are called where they are counted. */
export const FILES: CountedWords = { one: 'file', many: 'files' };

/** Files counted with what they have done: "3 files have changed". */
export const FILES_HAVING: CountedWords = { one: 'file has', many: 'files have' };

/** What a story's steps are called where they are counted, and one of them inside a sentence. */
export const STEPS: CountedWords = { one: 'step', many: 'steps' };

/** What the reader's comments are called where they are counted. */
export const COMMENTS: CountedWords = { one: 'comment', many: 'comments' };

/** What everything said under the comment that opened a thread is called, counted: the agent's and the reader's alike. */
export const REPLIES: CountedWords = { one: 'reply', many: 'replies' };

/** The words that go with a count, said without it: the singular for one, the plural for none and for many. */
export function wordsFor(count: number, words: CountedWords): string {
	return count === 1 ? words.one : words.many;
}

// How a count is written: in the page's own language, its thousands set apart, "3,608"
const COUNT_WRITTEN = new Intl.NumberFormat('en');

/** A count and the words that go with it: "1 file", "0 files", "3,608 names". */
export function counted(count: number, words: CountedWords): string {
	return `${COUNT_WRITTEN.format(count)} ${wordsFor(count, words)}`;
}
