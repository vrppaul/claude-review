import { describe, it, expect } from 'vitest';
import { fileTree, type TreeNode } from '$lib/utils/file-tree';
import { diffFile } from './diff';

/** The tree as rows a reader sees: each name, set in by how deep it is, folders with a slash. */
function rowsOf(nodes: TreeNode[], depth = 0): string[] {
	return nodes.flatMap((node) =>
		node.kind === 'file'
			? [`${'  '.repeat(depth)}${node.name}`]
			: [`${'  '.repeat(depth)}${node.name}/`, ...rowsOf(node.children, depth + 1)]
	);
}

function treeOf(...paths: string[]) {
	return fileTree(paths.map((path) => diffFile({ path })));
}

describe('the files of a review as a tree', () => {
	it('puts each file in the folders its path names', () => {
		expect(rowsOf(treeOf('src/a.ts', 'src/b.ts', 'README.md'))).toEqual(['src/', '  a.ts', '  b.ts', 'README.md']);
	});

	it('keeps the order the review lists the files in, a folder where its first file is', () => {
		expect(rowsOf(treeOf('b.ts', 'src/z.ts', 'a.ts', 'src/y.ts'))).toEqual([
			'b.ts',
			'src/',
			'  z.ts',
			'  y.ts',
			'a.ts'
		]);
	});

	it('draws a chain of folders that each hold one folder as one row, however long', () => {
		const tree = treeOf('src/lib/components/one.ts', 'src/lib/components/two.ts');

		expect(rowsOf(tree)).toEqual(['src/lib/components/', '  one.ts', '  two.ts']);
	});

	it('stops the chain at a folder that holds a file of its own', () => {
		const tree = treeOf('src/lib/one.ts', 'src/lib/deep/two.ts');

		expect(rowsOf(tree)).toEqual(['src/lib/', '  one.ts', '  deep/', '    two.ts']);
	});

	it('knows a folder by its path from the top, the way it is folded', () => {
		const [folder] = treeOf('src/lib/one.ts', 'src/lib/two.ts');

		expect(folder.path).toBe('src/lib');
	});

	it('keeps the file a row stands for', () => {
		const [readme] = treeOf('README.md');

		expect(readme.kind === 'file' && readme.file.path).toBe('README.md');
	});
});
