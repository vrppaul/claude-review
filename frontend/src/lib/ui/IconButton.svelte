<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { BUTTON_SIZES, BUTTON_TONES, type ButtonSize, type ButtonTone } from './button';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-label' | 'title'> {
		tone: ButtonTone;
		size: ButtonSize;
		/** What it does, in words: said to whoever cannot see its icon, and shown under the pointer. */
		label: string;
		testId: string;
		/** The button itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
		/** Its icon, drawn at the size the button gives it. */
		children: Snippet;
		/** A figure on its corner, a notification's: how many of what it opens wait (a Count). */
		corner?: Snippet | undefined;
	}

	let { tone, size, label, testId, element = $bindable(), children, corner, ...attributes }: Props = $props();
</script>

<!-- A button that is an icon alone: as tall as it is wide, its words kept for whoever cannot see the icon -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	aria-label={label}
	title={label}
	data-testid={testId}
	class={['cr-ui-button cr-ui-icon-button cr-pressable', BUTTON_TONES[tone], BUTTON_SIZES[size]]}
>
	{@render children()}
	{#if corner}
		<span class="cr-ui-icon-button-corner">{@render corner()}</span>
	{/if}
</button>
