<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { CARD_HANGINGS, CARD_TONES, type CardHanging, type CardTone } from './card';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		tone: CardTone;
		/** Where it hangs under what it is about; none for a card that stands where it is drawn. */
		hangs?: CardHanging | undefined;
		testId: string;
		/** The bar that heads it (CardBar), the same open and folded; none for a card with one room round what it holds. */
		bar?: Snippet | undefined;
		/** What it holds; none for a card folded to its bar. */
		children?: Snippet | undefined;
		/** What stands at its foot, under what it holds: a card headed by a bar alone has one. */
		foot?: Snippet | undefined;
		/** Whether what it holds is not there yet, a comment being written: drawn as the card it becomes, on a dashed edge. */
		beingWritten?: boolean;
	}

	let { tone, hangs, testId, bar, children, foot, beingWritten = false, ...attributes }: Props = $props();
</script>

<!-- What it holds boxed apart from what stands round it, edged in its tone's colour (lib/ui/card.ts); where it
	hangs under what it is about, lifted off that and pointing up at it. Headed by a bar, it is laid out by its
	parts, each on the card's room either side; else one room round what it holds -->
<div
	{...attributes}
	data-testid={testId}
	class={[
		'cr-ui-card',
		bar ? 'cr-ui-card-barred' : 'cr-ui-card-content',
		CARD_TONES[tone],
		hangs && CARD_HANGINGS[hangs],
		beingWritten && 'cr-ui-card-being-written'
	]}
>
	{@render bar?.()}
	{#if bar && children}
		<div class="cr-ui-card-body">{@render children()}</div>
	{:else}
		{@render children?.()}
	{/if}
	{#if foot}
		<div class="cr-ui-card-foot">{@render foot()}</div>
	{/if}
</div>
