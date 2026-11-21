/**
 * The files of a review as a tree of the folders they are in: the way a
 * reader looks for a file, by where it lives.
 *
 * Files keep the order the review lists them in, and a folder stands where
 * its first file does. A folder that holds nothing but one other folder is
 * one row with it — "src/lib/components" — rather than a staircase of rows,
 * each opening onto the next.
 *
 * Under a file it lists the names the change touched in it, where names are
 * listed. A filter leaves a file whose path holds what the reader typed, or
 * one of whose names does, and under a file whose path does not, only those
 * names: both matched whatever their case.
 */

import type { DiffFile, TouchedName } from '$lib/types';
import { fileName, PATH_SEPARATOR } from '$lib/utils/paths';

/** A file the tree lists, and the names it lists under it. */
export interface ListedFile {
	file: DiffFile;
	names: readonly TouchedName[];
}

/** A folder of the tree, and what it holds. */
export interface TreeFolder {
	kind: 'folder';
	/** What its row says: its own name, or the names of the folders it stands for. */
	name: string;
	/** Its path from the top, which it is folded by. */
	path: string;
	children: TreeNode[];
}

/** A file of the tree, by its own name, and the names listed under it. */
interface TreeFile {
	kind: 'file';
	name: string;
	path: string;
	listed: ListedFile;
}

export type TreeNode = TreeFolder | TreeFile;

/**
 * The files a filter leaves, each with the names it lists under it: all of them where the file's path holds what
 * was typed, else those that hold it.
 *
 * @param namesOf the names the tree lists under a file, none where it lists no names
 * @param sought what the reader typed, lower-cased; everything holds it while it is empty
 */
export function filesFound(
	files: readonly DiffFile[],
	namesOf: (path: string) => readonly TouchedName[],
	sought: string
): ListedFile[] {
	return files.flatMap((file) => foundIn(file, namesOf(file.path), sought));
}

/** A file as the filter leaves it, if it does. */
function foundIn(file: DiffFile, names: readonly TouchedName[], sought: string): ListedFile[] {
	if (holds(file.path, sought)) return [{ file, names }];
	const answering = names.filter((name) => holds(name.name, sought));
	return answering.length === 0 ? [] : [{ file, names: answering }];
}

/** Whether words hold what the reader typed, whatever their case. */
function holds(words: string, sought: string): boolean {
	return words.toLowerCase().includes(sought);
}

export function fileTree(files: readonly ListedFile[]): TreeNode[] {
	const top: TreeNode[] = [];
	for (const listed of files) addFile(top, listed);
	return top.map(collapsed);
}

/** Put a file in the folders its path names, making each the first time a file is in it. */
function addFile(top: TreeNode[], listed: ListedFile): void {
	const { path } = listed.file;
	const folders = path.split(PATH_SEPARATOR).slice(0, -1);
	let siblings = top;
	for (const [depth, name] of folders.entries()) {
		const folderPath = folders.slice(0, depth + 1).join(PATH_SEPARATOR);
		siblings = folderAmong(siblings, name, folderPath).children;
	}
	siblings.push({ kind: 'file', name: fileName(path), path, listed });
}

/** The folder at a path among a folder's children, put there if it is not yet. */
function folderAmong(siblings: TreeNode[], name: string, path: string): TreeFolder {
	const found = siblings.find((node): node is TreeFolder => node.kind === 'folder' && node.path === path);
	if (found) return found;
	const made: TreeFolder = { kind: 'folder', name, path, children: [] };
	siblings.push(made);
	return made;
}

/** A folder holding one folder and nothing else, made one row with it, as far down as that goes. */
function collapsed(node: TreeNode): TreeNode {
	if (node.kind === 'file') return node;
	const [only, ...others] = node.children;
	if (only?.kind === 'folder' && others.length === 0) {
		return collapsed({ ...only, name: `${node.name}${PATH_SEPARATOR}${only.name}` });
	}
	return { ...node, children: node.children.map(collapsed) };
}
