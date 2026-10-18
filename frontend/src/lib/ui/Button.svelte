<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { BUTTON_SIZES, BUTTON_TONES, type ButtonSize, type ButtonTone } from './button';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children'> {
		/** What it is to the reader beside its neighbours. */
		tone: ButtonTone;
		size: ButtonSize;
		/** The button itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
		/** What it says: its words, an icon before them. */
		children: Snippet;
	}

	let { tone, size, element = $bindable(), children, ...attributes }: Props = $props();
</script>

<!-- A button of the page, drawn as its tone and size say: what it is handed besides lands on the element, and
	its look is the library's alone, written after it -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	class={['cr-ui-button cr-pressable', BUTTON_TONES[tone], BUTTON_SIZES[size]]}
>
	{@render children()}
</button>
