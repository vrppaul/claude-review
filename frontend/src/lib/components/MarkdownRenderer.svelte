<script lang="ts" module>
	import { Marked, type Tokens } from 'marked';
	import { markedHighlight } from 'marked-highlight';
	import { hljs } from '$lib/utils/highlight';
	import { escapeMarkup, isAbsoluteDestination } from '$lib/utils/safe-markup';
	import Prose from '$lib/ui/Prose.svelte';

	// Where a link opens: a tab of its own, which learns nothing of the review
	// that opened it — followed in the review's own tab, it would end the review
	const IN_A_TAB_OF_ITS_OWN = 'target="_blank" rel="noopener noreferrer"';
	// What an image is called in the words that stand for it
	const IMAGE = 'image';

	/** A title attribute, or nothing when the destination has no title. */
	function titleAttribute(title: string | null | undefined): string {
		return title ? ` title="${escapeMarkup(title)}"` : '';
	}

	/** An image in words: what it shows, if the text says, and where it is. */
	function imageInWords(token: Tokens.Image): string {
		const shows = token.text ? `${IMAGE}: ${token.text}` : IMAGE;
		return escapeMarkup(`${shows} (${token.href})`);
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
				/**
				 * An image named in words, in the line it stands in, rather than
				 * drawn. A path is read against the review's own address, which
				 * serves no file of the repository — `assets/…` would even reach the
				 * page's own scripts — and the page's policy loads no image from
				 * anywhere else, so a picture would only arrive broken. One written
				 * whole opens, like a link, in a tab of its own.
				 */
				image(token: Tokens.Image) {
					const words = `<span class="cr-image-named">${imageInWords(token)}</span>`;
					if (!isAbsoluteDestination(token.href)) return words;
					return `<a href="${escapeMarkup(token.href)}"${titleAttribute(token.title)} ${IN_A_TAB_OF_ITS_OWN}>${words}</a>`;
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

<Prose {dense} testId="markdown-content">
	{@html html}
</Prose>
