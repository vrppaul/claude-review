<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import {
		CARD_HANGINGS,
		CARD_TONES,
		OPENING_FADES,
		type CardHanging,
		type CardOpening,
		type CardTone,
		type WashedTone
	} from './card';
	import Unfolding from './Unfolding.svelte';

	/**
	 * Whose it is, or where what it holds stands; and whether its tone's wash lies over the whole of it, a line of
	 * a story in short, in place of the card's ground, which only a tone a card is washed in can.
	 */
	type Washing = { tone: CardTone; washed?: false } | { tone: WashedTone; washed: true };

	/**
	 * The bar that heads it (CardBar), the same open and folded, and what stands at its foot, under what it holds,
	 * and how what stands under the bar comes in as the reader opens it, if they just did; or none of them, for a
	 * card with one room round what it holds.
	 */
	type Heading =
		| { bar: Snippet; foot?: Snippet | undefined; opening?: CardOpening | undefined }
		| { bar?: undefined; foot?: undefined; opening?: undefined };

	interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		/** Where it hangs under what it is about; none for a card that stands where it is drawn. */
		hangs?: CardHanging | undefined;
		testId: string;
		/** What it holds; none for a card folded to its bar. */
		children?: Snippet | undefined;
		/** Whether what it holds is not there yet, a comment being written: drawn as the card it becomes, on a dashed edge. */
		beingWritten?: boolean;
	}

	type Props = CardProps & Washing & Heading;

	let {
		tone,
		hangs,
		testId,
		bar,
		children,
		foot,
		beingWritten = false,
		opening,
		washed = false,
		...attributes
	}: Props = $props();
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
		beingWritten && 'cr-ui-card-being-written',
		washed && 'cr-ui-card-washed'
	]}
>
	{@render bar?.()}
	{#if bar}
		<!-- What stands under its bar, its body and its foot, coming down as one where the reader opens it; folded,
			nothing, so the bar is all of it -->
		{#if children || foot}
			<Unfolding
				byReader={opening !== undefined}
				fading={opening !== undefined && OPENING_FADES[opening]}
				testId="{testId}-under-its-bar"
			>
				{#if children}
					<div class="cr-ui-card-body">{@render children()}</div>
				{/if}
				{#if foot}
					<div class="cr-ui-card-foot">{@render foot()}</div>
				{/if}
			</Unfolding>
		{/if}
	{:else}
		{@render children?.()}
	{/if}
</div>
