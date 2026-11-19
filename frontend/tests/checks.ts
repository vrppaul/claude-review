/** The checks the agent reported, as the review holds them and sends them to the page. */
import type { Check, CheckFailure } from '$lib/types';

// When a check was reported, unless a test says: 13:02 on a day in November, in the time of whoever runs the tests
export const REPORTED_AT = new Date(2026, 10, 19, 13, 2).getTime();

/** A place a check failed, unless a test says otherwise. */
export function failure(given: Partial<CheckFailure> = {}): CheckFailure {
	return { path: 'a.py', line: 1, what: 'test_it', why: null, ...given };
}

/** A check that passed on the code as it stands, in the first round, unless a test says otherwise. */
export function check(given: Partial<Check> = {}): Check {
	return {
		name: 'pytest',
		status: 'passed',
		summary: null,
		failures: [],
		round: 1,
		at: REPORTED_AT,
		changed_since: [],
		out_of_date: false,
		...given
	};
}

/** A check that failed where its failures say, on the code as it stands. */
export function failedCheck(failures: CheckFailure[], given: Partial<Check> = {}): Check {
	return check({ status: 'failed', failures, ...given });
}

/** A check the code moved on from: these files changed after it ran. */
export function outOfDateCheck(changed: string[], given: Partial<Check> = {}): Check {
	return check({ changed_since: changed, out_of_date: true, ...given });
}
