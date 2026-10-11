/**
 * The paths of the files under review, as the server writes them: the
 * folders a file is in, each followed by a slash, then its name.
 */

/** What stands between a folder and what it holds, in a path. */
export const PATH_SEPARATOR = '/';

/** A file's own name, without the folders it is in. */
export function fileName(path: string): string {
	return path.split(PATH_SEPARATOR).at(-1) ?? path;
}

/** The folders a path is in, as written before its name: empty for a file at the top. */
function folderOf(path: string): string {
	return path.slice(0, path.lastIndexOf(PATH_SEPARATOR) + 1);
}

/**
 * What a moved file was called, said beside its name where it stands now:
 * its old name, if it stayed in its folder, or its old path, if it came
 * from another.
 */
export function formerName(oldPath: string, newPath: string): string {
	return folderOf(oldPath) === folderOf(newPath) ? fileName(oldPath) : oldPath;
}
