/** What the ids of the reader's panel messages begin with: an answer names one. */
export const MESSAGE_ID_PREFIX = 'panel-';
/** What the ids of the agent's answers in the panel begin with. */
export const ANSWER_ID_PREFIX = 'answer-';
/** What the ids of the review's own notes in the panel begin with. */
export const EVENT_ID_PREFIX = 'event-';
/** What the ids of the reader's threads begin with. */
export const COMMENT_ID_PREFIX = 'comment-';
/** What the ids of turns in a thread begin with: a question asked in one names it. */
export const TURN_ID_PREFIX = 'turn-';

/**
 * Ids the browser hands out: a kind and a number, in order.
 *
 * Short and readable on purpose. The agent names threads and questions by
 * them — `claude-review reply --thread comment-3` — and reads them in every
 * event, so a random string would cost it on every turn.
 *
 * A review restored from its draft carries on from how many it had handed
 * out — kept in the draft, because a thread deleted before the reload leaves
 * no id behind, and the agent may still name it. A draft from before that
 * was kept carries on past the highest id it holds.
 */
export class IdSequence {
	private last = 0;

	constructor(private readonly prefix: string) {}

	/** How many ids of this kind have been handed out, for a draft to keep. */
	get issued(): number {
		return this.last;
	}

	/** Carry on from what a draft says was handed out before the reload. */
	continueFrom(issued: number): void {
		this.last = Math.max(this.last, issued);
	}

	/** The next id of this kind. */
	next(): string {
		this.last += 1;
		return `${this.prefix}${this.last}`;
	}

	/**
	 * Carry on past every id of this kind among these. Ids of other kinds, and
	 * the missing ids of what was written before ids existed, are passed over.
	 */
	continuePast(ids: Iterable<string | undefined>): void {
		for (const id of ids) {
			if (id === undefined || !id.startsWith(this.prefix)) continue;
			const number = Number(id.slice(this.prefix.length));
			if (Number.isInteger(number) && number > 0) {
				this.last = Math.max(this.last, number);
			}
		}
	}

	/** Start over, for a review that holds nothing yet. */
	reset(): void {
		this.last = 0;
	}
}
