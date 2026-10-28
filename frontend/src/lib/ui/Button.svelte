<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { buttonLook, type ButtonSize, type ButtonTone } from './button';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children'> {
		/** What it is to the reader beside its neighbours. */
		tone: ButtonTone;
		size: ButtonSize;
		testId: string;
		/**
		 * Whether it is one of the ways on a pane lists, one under another: across the pane, its words at its start,
		 * so the ways read down as a list; none for a button among others in a line.
		 */
		listed?: boolean;
		/** What a way a pane lists says of itself at its end, quieter than its words: "7 stops", "draft kept". */
		note?: string | undefined;
		/** The button itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
		/** What it says: its words, an icon before them; or its icon alone, where its words may give way to it. */
		children: Snippet;
		/**
		 * Its words, after its icon, where the room it stands in (a container named button-room) may grow too narrow
		 * for them: there they give way, kept for a screen reader, and the icon stands alone, square as an icon
		 * button's. None where its words are among its children.
		 */
		wordsGivingWay?: string | undefined;
	}

	let {
		tone,
		size,
		testId,
		listed = false,
		note,
		element = $bindable(),
		children,
		wordsGivingWay,
		...attributes
	}: Props = $props();
</script>

<!-- A button of the page, drawn as its tone and size say: what it is handed besides lands on the element, and
	its test id and look are the library's alone, written after it -->
<button bind:this={element} type="button" {...attributes} data-testid={testId} class={buttonLook(tone, size, listed)}>
	{@render children()}{#if wordsGivingWay}<span class="cr-ui-button-words-giving-way @max-cr-narrow/button-room:sr-only"
			>{wordsGivingWay}</span
		>{/if}{#if note}<span class="cr-ui-button-note">{note}</span>{/if}
</button>
