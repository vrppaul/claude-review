/**
 * What two lines have in common, token by token: the longest run of tokens
 * both have in the same order, though not necessarily side by side. What is
 * left over on either side is what changed.
 */

/** A token of a line — a word, a run of spaces, a mark — and whether the other line has it too. */
export interface Token {
	text: string;
	kept: boolean;
}

/** Both lines' tokens, each marked kept where it is part of what the lines have in common. */
interface CommonTokens {
	before: Token[];
	after: Token[];
}

/**
 * How many tokens two lines have in common from any pair of places in them
 * to their ends. Its last row and column stand past the end of one line or
 * the other, where nothing is left in common, and stay zero.
 */
class CommonLengths {
	readonly #width: number;
	readonly #lengths: number[];

	constructor(before: readonly string[], after: readonly string[]) {
		this.#width = after.length + 1;
		this.#lengths = new Array<number>((before.length + 1) * this.#width).fill(0);
		// Filled from the ends back: each place reads the places after it
		for (let beforeIndex = before.length - 1; beforeIndex >= 0; beforeIndex -= 1) {
			for (let afterIndex = after.length - 1; afterIndex >= 0; afterIndex -= 1) {
				this.#lengths[this.#cellOf(beforeIndex, afterIndex)] =
					before[beforeIndex] === after[afterIndex]
						? this.at(beforeIndex + 1, afterIndex + 1) + 1
						: Math.max(this.at(beforeIndex + 1, afterIndex), this.at(beforeIndex, afterIndex + 1));
			}
		}
	}

	/** How many tokens the lines have in common from these places to their ends. */
	at(beforeIndex: number, afterIndex: number): number {
		return this.#lengths[this.#cellOf(beforeIndex, afterIndex)] ?? 0;
	}

	#cellOf(beforeIndex: number, afterIndex: number): number {
		return beforeIndex * this.#width + afterIndex;
	}
}

/** Each line's tokens, those the two lines have in common marked kept. */
export function commonTokens(before: readonly string[], after: readonly string[]): CommonTokens {
	const lengths = new CommonLengths(before, after);
	const keptBefore = new Set<number>();
	const keptAfter = new Set<number>();
	let beforeIndex = 0;
	let afterIndex = 0;
	// From the start: a token both lines have here is kept; otherwise the one
	// passed over is whichever leaves more in common after it
	while (beforeIndex < before.length && afterIndex < after.length) {
		if (before[beforeIndex] === after[afterIndex]) {
			keptBefore.add(beforeIndex);
			keptAfter.add(afterIndex);
			beforeIndex += 1;
			afterIndex += 1;
		} else if (lengths.at(beforeIndex + 1, afterIndex) >= lengths.at(beforeIndex, afterIndex + 1)) {
			beforeIndex += 1;
		} else {
			afterIndex += 1;
		}
	}
	return { before: tokensOf(before, keptBefore), after: tokensOf(after, keptAfter) };
}

function tokensOf(texts: readonly string[], kept: ReadonlySet<number>): Token[] {
	return texts.map((text, index) => ({ text, kept: kept.has(index) }));
}
