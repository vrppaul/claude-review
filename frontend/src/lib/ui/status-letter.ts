/**
 * What became of a file (StatusLetter), said as a letter in the change's own
 * colour beside its name: changed, added and deleted each in its own; moved,
 * quietly, as blue is the reader's own mark and nothing else's. Its look is
 * written in styles/ui.css.
 */
export type Became = 'changed' | 'added' | 'deleted' | 'moved';

// The class of each in the library's stylesheet
export const BECAME: Record<Became, string> = {
	changed: 'cr-ui-status-changed',
	added: 'cr-ui-status-added',
	deleted: 'cr-ui-status-deleted',
	moved: 'cr-ui-status-moved'
};
