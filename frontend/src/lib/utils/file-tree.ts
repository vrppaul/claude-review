/**
 * The files of a review as a tree of the folders they are in: the way a
 * reader looks for a file, by where it lives.
 *
 * Files keep the order the review lists them in, and a folder stands where
 * its first file does. A folder that holds nothing but one other folder is
 * one row with it — "src/lib/components" — rather than a staircase of rows,
 * each opening onto the next.
 */

import type { DiffFile } from '$lib/types';
import { fileName, PATH_SEPARATOR } from '$lib/utils/paths';

/** A folder of the tree, and what it holds. */
interface TreeFolder {
	kind: 'folder';
	/** What its row says: its own name, or the names of the folders it stands for. */
	name: string;
	/** Its path from the top, which it is folded by. */
	path: string;
	children: TreeNode[];
}

/** A file of the tree, by its own name. */
interface TreeFile {
	kind: 'file';
	name: string;
	path: string;
	file: DiffFile;
}

export type TreeNode = TreeFolder | TreeFile;

export function fileTree(files: readonly DiffFile[]): TreeNode[] {
	const top: TreeNode[] = [];
	for (const file of files) addFile(top, file);
	return top.map(collapsed);
}

/** Put a file in the folders its path names, making each the first time a file is in it. */
function addFile(top: TreeNode[], file: DiffFile): void {
	const folders = file.path.split(PATH_SEPARATOR).slice(0, -1);
	let siblings = top;
	for (const [depth, name] of folders.entries()) {
		const path = folders.slice(0, depth + 1).join(PATH_SEPARATOR);
		siblings = folderAmong(siblings, name, path).children;
	}
	siblings.push({ kind: 'file', name: fileName(file.path), path: file.path, file });
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
	const [only] = node.children;
	if (node.children.length === 1 && only.kind === 'folder') {
		return collapsed({ ...only, name: `${node.name}${PATH_SEPARATOR}${only.name}` });
	}
	return { ...node, children: node.children.map(collapsed) };
}
