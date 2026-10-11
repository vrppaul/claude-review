import hljs from 'highlight.js/lib/core';

import type { DiffLine, ReviewMode } from '$lib/types';
import { escapeMarkup } from '$lib/utils/safe-markup';

export { hljs };

// Register common languages
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import css from 'highlight.js/lib/languages/css';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import bash from 'highlight.js/lib/languages/bash';
import yaml from 'highlight.js/lib/languages/yaml';
import markdown from 'highlight.js/lib/languages/markdown';
import rust from 'highlight.js/lib/languages/rust';
import golang from 'highlight.js/lib/languages/go';
import sql from 'highlight.js/lib/languages/sql';

hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('css', css);
hljs.registerLanguage('json', json);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('rust', rust);
hljs.registerLanguage('go', golang);
hljs.registerLanguage('sql', sql);

// What a file is highlighted as, by the extension its name ends in
const LANGUAGE_BY_EXTENSION: Record<string, string> = {
	'.js': 'javascript',
	'.mjs': 'javascript',
	'.cjs': 'javascript',
	'.jsx': 'javascript',
	'.ts': 'typescript',
	'.tsx': 'typescript',
	'.py': 'python',
	'.css': 'css',
	'.json': 'json',
	'.html': 'html',
	'.htm': 'html',
	'.xml': 'xml',
	'.svg': 'xml',
	'.sh': 'bash',
	'.bash': 'bash',
	'.zsh': 'bash',
	'.yml': 'yaml',
	'.yaml': 'yaml',
	'.md': 'markdown',
	'.rs': 'rust',
	'.go': 'go',
	'.sql': 'sql',
	'.svelte': 'html'
};

/** What a file is highlighted as, by its extension. */
function detectLanguage(filePath: string): string | null {
	const lastDot = filePath.lastIndexOf('.');
	if (lastDot === -1) return null;
	const extension = filePath.slice(lastDot).toLowerCase();
	return LANGUAGE_BY_EXTENSION[extension] ?? null;
}

/**
 * What each kind of review reads its files as. A diff and plain files go by
 * their names; a transcript's entries are labels like "user (22:41) #1",
 * with no extension, and their text is prose, which reads best as markdown.
 */
const LANGUAGE_IN: Record<ReviewMode, (path: string) => string | null> = {
	diff: detectLanguage,
	files: detectLanguage,
	transcript: () => 'markdown'
};

/** What a file of this kind of review is highlighted and rendered as, if anything. */
export function languageOf(mode: ReviewMode, path: string): string | null {
	return LANGUAGE_IN[mode](path);
}

/** A line of a hunk with its text as it is drawn: highlighted, and escaped either way. */
export interface HighlightedLine {
	line: DiffLine;
	markup: string;
}

/**
 * Highlight the lines of a hunk, each with the markup of its own text.
 *
 * Highlighting row by row cannot see a construct that spans lines — a
 * docstring, a block comment, a template literal — and colours each
 * continuation as if it began a fresh statement. So each hunk is highlighted
 * as a document instead.
 *
 * A hunk holds two versions of the same region interleaved, and only one of
 * them is real code at a time: a removed line may open a string that the line
 * replacing it never opens. Each side is therefore assembled and highlighted
 * on its own, and every row takes the markup from the side it belongs to.
 * Hunks are highlighted separately because the gaps between them are not part
 * of the file, so state must not carry across one.
 */
export function highlightHunk(lines: DiffLine[], language: string | null): HighlightedLine[] {
	if (!language) return lines.map((line) => ({ line, markup: escapeMarkup(line.content) }));

	const hasRemovals = lines.some((line) => line.kind === 'delete');
	const newSide = sideLines(lines, 'add', language);
	const oldSide = hasRemovals ? sideLines(lines, 'delete', language) : newSide;

	// Each line takes its markup from the side it belongs to, and moves on the
	// reader of every side it is on: context is on both
	const highlighted: HighlightedLine[] = [];
	let oldAt = 0;
	let newAt = 0;
	for (const line of lines) {
		const markup = (line.kind === 'delete' ? oldSide[oldAt] : newSide[newAt]) ?? escapeMarkup(line.content);
		highlighted.push({ line, markup });
		if (line.kind !== 'add') oldAt += 1;
		if (line.kind !== 'delete') newAt += 1;
	}
	return highlighted;
}

/** Highlight one version of a hunk: its context plus the lines exclusive to that side. */
function sideLines(lines: DiffLine[], exclusive: DiffLine['kind'], language: string): string[] {
	const text = lines
		.filter((line) => line.kind === 'context' || line.kind === exclusive)
		.map((line) => line.content)
		.join('\n');

	try {
		return splitHighlighted(hljs.highlight(text, { language, ignoreIllegals: true }).value);
	} catch {
		return text.split('\n').map(escapeMarkup);
	}
}

// What closes every span the highlighter opens
const SPAN_CLOSE = '</span>';

/**
 * Cut highlighted markup into one string per line.
 *
 * A span may run across a newline, so every span still open at a break is
 * closed before the line ends and reopened at the start of the next one —
 * otherwise each line would be invalid markup on its own.
 */
function splitHighlighted(html: string): string[] {
	const lines: string[] = [];
	const open: string[] = [];
	let current = '';
	let position = 0;

	while (position < html.length) {
		const character = html.charAt(position);

		if (character === '<') {
			const close = html.indexOf('>', position);
			if (close === -1) {
				current += html.slice(position);
				break;
			}
			const tag = html.slice(position, close + 1);
			if (tag.startsWith('</')) open.pop();
			else if (!tag.endsWith('/>')) open.push(tag);
			current += tag;
			position = close + 1;
			continue;
		}

		if (character === '\n') {
			lines.push(current + SPAN_CLOSE.repeat(open.length));
			current = open.join('');
			position += 1;
			continue;
		}

		current += character;
		position += 1;
	}

	lines.push(current + SPAN_CLOSE.repeat(open.length));
	return lines;
}
