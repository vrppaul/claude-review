import type { FileStatus, NameChange } from '$lib/types';
import type { Became } from '$lib/ui/status-letter';

/** How a file's status is said in a letter (lib/ui StatusLetter), and what became of the file, which colours it. */
interface StatusLetter {
	letter: string;
	became: Became;
}

export const STATUS_LETTERS: Record<FileStatus, StatusLetter> = {
	modified: { letter: 'M', became: 'changed' },
	added: { letter: 'A', became: 'added' },
	deleted: { letter: 'D', became: 'deleted' },
	renamed: { letter: 'R', became: 'moved' }
};

/** What became of a name the change touched, said in the letter of a file that became the same. */
export const NAME_LETTERS: Record<NameChange, StatusLetter> = {
	added: STATUS_LETTERS.added,
	modified: STATUS_LETTERS.modified,
	removed: STATUS_LETTERS.deleted
};
