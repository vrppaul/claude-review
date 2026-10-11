<script lang="ts" module>
	import { Marked, type Tokens } from 'marked';
	import { markedHighlight } from 'marked-highlight';
	import { hljs } from '$lib/utils/highlight';
	import { escapeMarkup, isAbsoluteDestination, isSafeDestination } from '$lib/utils/safe-markup';

	// Where a link opens: a tab of its own, which learns nothing of the review
	// that opened it — followed in the review's own tab, it would end the review
	const IN_A_TAB_OF_ITS_OWN = 'target="_blank" rel="noopener noreferrer"';

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
				/**
				 * A link that leads somewhere of its own, opened in a tab of its
				 * own. Anything else — code in place of a destination, or a path
				 * relative to the review's own address — is left as its text.
				 */
				link(token: Tokens.Link) {
					const text = this.parser.parseInline(token.tokens);
					if (!isAbsoluteDestination(token.href)) return text;
					return `<a href="${escapeMarkup(token.href)}"${titleAttribute(token.title)} ${IN_A_TAB_OF_ITS_OWN}>${text}</a>`;
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

	// Parsed as it is drawn: nothing in this setup waits on anything
	const html = $derived(marked.parse(text, { async: false }));
</script>

<div data-testid="markdown-content" class={['cr-prose prose prose-sm', dense && 'cr-comment-body']}>
	{@html html}
</div>
