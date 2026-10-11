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
