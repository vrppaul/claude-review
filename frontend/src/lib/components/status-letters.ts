import type { FileStatus } from '$lib/types';

/** How a file's status is said in a letter, and the colour of the change it stands for. */
interface StatusLetter {
	letter: string;
	colour: string;
}

// A letter in the change's own colour, rather than a filled disc: the file
// name is what the eye should land on beside it. A moved file says so
// quietly — blue is the reader's own mark, and nothing else's.
export const STATUS_LETTERS: Record<FileStatus, StatusLetter> = {
	modified: { letter: 'M', colour: 'text-(--cr-status-modified)' },
	added: { letter: 'A', colour: 'text-(--cr-add-text)' },
	deleted: { letter: 'D', colour: 'text-(--cr-del-text)' },
	renamed: { letter: 'R', colour: 'cr-muted' }
};
