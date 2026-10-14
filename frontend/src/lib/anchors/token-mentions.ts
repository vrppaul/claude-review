/**
 * Where a message mentions a thread by its token, whatever the thread hangs on.
 *
 * A token can stand at the start of a longer one — `@a.py:1-2` in
 * `@a.py:1-20`, `@story:doubt` in `@story:doubt:why` — so a mention is the
 * token where what follows does not carry it on. What carries a token on
 * depends on what its kind's tokens are made of, and each kind says it.
 */

/** Where a text mentions a token and not a longer one that starts the same: where each mention starts. */
export function mentionStarts(text: string, token: string, carriesOn: RegExp): number[] {
	const starts: number[] = [];
	for (let from = text.indexOf(token); from !== -1; from = text.indexOf(token, from + token.length)) {
		if (!carriesOn.test(text.slice(from + token.length))) starts.push(from);
	}
	return starts;
}
