/**
 * How a check stands, as its row (CheckRow) draws it:
 * - failing: it failed on the code on screen, what the reader came for: a block on the error's tint, folding
 *   where it failed
 * - passing: it passed on the code on screen
 * - failed-before, passed-before: it ran before the code changed, its mark and name stepped back to ink
 */
export type CheckStands = 'failing' | 'passing' | 'failed-before' | 'passed-before';
