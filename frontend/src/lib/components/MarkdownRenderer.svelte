<script lang="ts" module>
	import { Marked, type Tokens } from 'marked';
	import { markedHighlight } from 'marked-highlight';
	import { hljs } from '$lib/utils/highlight';
	import { escapeMarkup, isSafeDestination } from '$lib/utils/safe-markup';

	/** A title attribute, or nothing when the destination has no title. */
	function titleAttribute(title: string | null | undefined): string {
		return title ? ` title="${escapeMarkup(title)}"` : '';
	}

	// Single shared instance — Marked is stateless once configured
	const marked = new Marked(
		markedHighlight({
			highlight(code: string, language: string) {
				if (language && hljs.getLanguage(language)) {
					return hljs.highlight(code, { language, ignoreIllegals: true }).value;
				}
				return code;
			}
		}),
		{
			renderer: {
				/**
				 * Show raw HTML rather than running it.
				 *
				 * The text being previewed is a file out of the repository under
				 * review, which may be a contributor's. Rendering its HTML would
				 * let `<img onerror>` run script with the review's own origin —
				 * able to read the diff, read repository files, and submit
				 * comments of its own for an agent to act on. Escaping it is also
				 * the more faithful preview: you are reading a file, not
				 * publishing it.
				 */
				html(token: Tokens.HTML | Tokens.Tag) {
					return escapeMarkup(token.text);
				},
				link(token: Tokens.Link) {
					const text = this.parser.parseInline(token.tokens);
					if (!isSafeDestination(token.href)) return text;
					return `<a href="${escapeMarkup(token.href)}"${titleAttribute(token.title)}>${text}</a>`;
				},
				image(token: Tokens.Image) {
					if (!isSafeDestination(token.href)) return escapeMarkup(token.text);
					return `<img src="${escapeMarkup(token.href)}" alt="${escapeMarkup(token.text)}"${titleAttribute(token.title)} />`;
				}
			}
		}
	);
</script>

<script lang="ts">
	interface Props {
		text: string;
		/** Inside a thread, where the reading face and measure are already set. */
		dense?: boolean;
	}

	let { text, dense = false }: Props = $props();

	const html = $derived(marked.parse(text) as string);
</script>

<div
	data-testid="markdown-content"
	class={dense ? 'cr-comment-body cr-prose prose prose-sm' : 'cr-prose prose prose-sm'}
>
	{@html html}
</div>
