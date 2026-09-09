<script lang="ts" module>
	import { Marked, type Tokens } from 'marked';
	import { markedHighlight } from 'marked-highlight';
	import { hljs } from '$lib/utils/highlight';

	function escapeHtml(text: string): string {
		return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	/** Schemes a link may use. Anything else — javascript:, data: — is not a
	 * destination, it is code, and a previewed file must not run any. */
	const SAFE_SCHEME = /^(?:https?:|mailto:|#|\/|\.{0,2}\/|[^a-z]|[a-z][a-z0-9+.-]*[^a-z0-9+.:-])/i;

	function isSafeHref(href: string): boolean {
		return SAFE_SCHEME.test(href.trim());
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
					return escapeHtml(token.text);
				},
				link(token: Tokens.Link) {
					const text = this.parser.parseInline(token.tokens);
					if (!isSafeHref(token.href)) return text;
					const title = token.title ? ` title="${escapeHtml(token.title)}"` : '';
					return `<a href="${escapeHtml(token.href)}"${title}>${text}</a>`;
				},
				image(token: Tokens.Image) {
					if (!isSafeHref(token.href)) return escapeHtml(token.text);
					const title = token.title ? ` title="${escapeHtml(token.title)}"` : '';
					return `<img src="${escapeHtml(token.href)}" alt="${escapeHtml(token.text)}"${title} />`;
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
