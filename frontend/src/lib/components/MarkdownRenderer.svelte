<script lang="ts" module>
	import { Marked } from 'marked';
	import { markedHighlight } from 'marked-highlight';
	import { hljs } from '$lib/utils/highlight';

	// Single shared instance — Marked is stateless once configured
	const marked = new Marked(
		markedHighlight({
			highlight(code: string, language: string) {
				if (language && hljs.getLanguage(language)) {
					return hljs.highlight(code, { language, ignoreIllegals: true }).value;
				}
				return code;
			}
		})
	);
</script>

<script lang="ts">
	interface Props {
		text: string;
	}

	let { text }: Props = $props();

	const html = $derived(marked.parse(text) as string);
</script>

<div data-testid="markdown-content" class="prose prose-sm max-w-none">
	{@html html}
</div>
