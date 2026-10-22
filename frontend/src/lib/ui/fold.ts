/**
 * What folds away and comes back — a thread, a file, a list of a story's
 * overview — is folded and unfolded by one act, named alike on every toggle
 * that does it (FoldToggle, ListsCardRow), to whoever cannot see its chevron.
 */

// The words the act is named by, round what it folds
const UNFOLD = 'Unfold';
const FOLD = 'Fold';
const AWAY = 'away';

/** What a press on a fold's toggle does to what it folds: "Unfold this thread", "Fold this thread away". */
export function foldToggleName(folded: boolean, subject: string): string {
	return folded ? `${UNFOLD} ${subject}` : `${FOLD} ${subject} ${AWAY}`;
}
