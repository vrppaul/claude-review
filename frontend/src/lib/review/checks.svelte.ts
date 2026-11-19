/**
 * The checks the agent reported running on the change — its tests, linters,
 * type checkers — as the review holds them: how each ended, and whether the
 * code moved on since. The review decides all of that; the page holds what
 * it last said, whole, and finds each file's failures in it.
 */

import type { Check, CheckFailure } from '$lib/types';

/** A place a check failed, with the check that says so. */
export interface FailureFound {
	/** The check that failed there, by its name. */
	check: string;
	/** Whether that check is out of date: a failure is as fresh as its check, whose result hangs on the whole tree. */
	outOfDate: boolean;
	failure: CheckFailure;
}

/** What a file, or a line, no check failed in holds. */
export const NO_FAILURES: readonly FailureFound[] = [];

/** Every place the checks failed, by the file it is in, in the order the checks say them. */
function failuresByFile(checks: readonly Check[]): ReadonlyMap<string, readonly FailureFound[]> {
	const found = checks.flatMap((check) =>
		check.failures.map((failure) => ({ check: check.name, outOfDate: check.out_of_date, failure }))
	);
	return Map.groupBy(found, ({ failure }) => failure.path);
}

export class Checks {
	#all: readonly Check[];
	// Asked for each file the tree lists and each file drawn, so grouped once a report
	readonly #byFile: ReadonlyMap<string, readonly FailureFound[]>;

	constructor(reported: readonly Check[]) {
		this.#all = $state.raw(reported);
		this.#byFile = $derived(failuresByFile(this.#all));
	}

	/** Every check the agent reported, as the review last said each stands. */
	get all(): readonly Check[] {
		return this.#all;
	}

	/** Take in the checks as the review says they stand now: every one, in place of those held. */
	take(reported: readonly Check[]): void {
		this.#all = reported;
	}

	/** The places the checks failed in a file. */
	failuresIn(path: string): readonly FailureFound[] {
		return this.#byFile.get(path) ?? NO_FAILURES;
	}
}
