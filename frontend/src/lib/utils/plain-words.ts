/**
 * What a comment says, in plain words on one line: for a place with room for
 * its first few — a folded thread, a row of the finish pane, a list of
 * replies — where Markdown's marks would be read as part of the words.
 *
 * Read by Markdown's own rules rather than by stripping marks off by
 * pattern: emphasis, code, links and lists lose their marks and keep their
 * words, and a suggested replacement is said as one rather than spelled
 * out fence and all.
 */

import { Marked, type Tokens } from 'marked';
import { splitSuggestions } from '$lib/utils/suggestion';

// What a suggested replacement in a comment is called on its line
const SUGGESTED = '(a suggested change)';
// Between two blocks of text read on one line
const BLOCK_BREAK = ' ';
const RUNS_OF_SPACE = /\s+/g;

// Every block said as its words, every inline mark dropped for what it marks
const plain = new Marked({
	renderer: {
		space: () => BLOCK_BREAK,
		hr: () => BLOCK_BREAK,
		def: () => BLOCK_BREAK,
		checkbox: () => '',
		html: ({ text }: Tokens.HTML | Tokens.Tag) => text,
		code: ({ text }: Tokens.Code) => `${text}${BLOCK_BREAK}`,
		heading({ tokens }: Tokens.Heading) {
			return `${this.parser.parseInline(tokens, this.parser.textRenderer)}${BLOCK_BREAK}`;
		},
		paragraph({ tokens }: Tokens.Paragraph) {
			return `${this.parser.parseInline(tokens, this.parser.textRenderer)}${BLOCK_BREAK}`;
		},
		text(token: Tokens.Text | Tokens.Escape) {
			return 'tokens' in token ? this.parser.parseInline(token.tokens, this.parser.textRenderer) : token.text;
		},
		blockquote({ tokens }: Tokens.Blockquote) {
			return this.parser.parse(tokens);
		},
		list({ items }: Tokens.List) {
			return items.map((item) => this.listitem(item)).join('');
		},
		listitem({ tokens }: Tokens.ListItem) {
			return `${this.parser.parse(tokens)}${BLOCK_BREAK}`;
		},
		table: ({ header, rows }: Tokens.Table) =>
			[header, ...rows].flatMap((cells) => cells.map((cell) => `${cell.text}${BLOCK_BREAK}`)).join('')
	}
});

/** A comment's words on one line, its marks dropped and a suggestion said as one. */
export function plainWords(markdown: string): string {
	return splitSuggestions(markdown)
		.map((part) => (part.kind === 'suggestion' ? SUGGESTED : plain.parse(part.text, { async: false })))
		.join(BLOCK_BREAK)
		.replace(RUNS_OF_SPACE, BLOCK_BREAK)
		.trim();
}
