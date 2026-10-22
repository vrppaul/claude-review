<script lang="ts">
	import type { Snippet } from 'svelte';
	import { TAG_TONES, type TagTone } from './tag';

	interface Props {
		tone: TagTone;
		/** What it says in full, shown under the pointer, where its words are short of that. */
		title?: string | undefined;
		testId: string;
		/** Its words, an icon before them. */
		children: Snippet;
	}

	let { tone, title, testId, children }: Props = $props();
</script>

<!-- A word or two said beside a heading or a name, on the chip of the colour of their tone (lib/ui/tag.ts) -->
<span data-testid={testId} {title} class={['cr-ui-tag', TAG_TONES[tone]]}>{@render children()}</span>
