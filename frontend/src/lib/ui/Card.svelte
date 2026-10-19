<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { CARD_HANGINGS, CARD_TONES, type CardHanging, type CardTone } from './card';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		tone: CardTone;
		/** Where it hangs under what it is about; none for a card that stands where it is drawn. */
		hangs?: CardHanging | undefined;
		testId: string;
		children: Snippet;
	}

	let { tone, hangs, testId, children, ...attributes }: Props = $props();
</script>

<!-- What it holds boxed apart from what stands round it, edged in its tone's colour (lib/ui/card.ts); where it
	hangs under what it is about, lifted off that and pointing up at it -->
<div {...attributes} data-testid={testId} class={['cr-ui-card', CARD_TONES[tone], hangs && CARD_HANGINGS[hangs]]}>
	{@render children()}
</div>
