<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { HEADING_KINDS, HEADING_TONES, type HeadingKind, type HeadingTag, type HeadingTone } from './heading';

	interface Props extends Omit<HTMLAttributes<HTMLElement>, 'class' | 'style' | 'children'> {
		tag: HeadingTag;
		/** What it heads, which sets its size and face. */
		heads: HeadingKind;
		/** The tone it is said in; the page's own words where it names none. */
		tone?: HeadingTone | undefined;
		/** Whether it is seen, or heard by a screen reader alone where what it heads is seen without it. */
		seen?: boolean;
		testId?: string | undefined;
		/** The heading itself, for whoever hands the keyboard to it. */
		element?: HTMLElement | undefined;
		/** What it says, and what stands before it: a part's number. */
		children: Snippet;
	}

	let { tag, heads, tone, seen = true, testId, element = $bindable(), children, ...attributes }: Props = $props();
</script>

<!-- A heading of the page, drawn as what it heads and its tone say: what it is handed besides lands on the
	element, and its test id and look are the library's alone, written after it -->
<svelte:element
	this={tag}
	bind:this={element}
	{...attributes}
	data-testid={testId}
	class={['cr-ui-heading', HEADING_KINDS[heads], tone && HEADING_TONES[tone], !seen && 'sr-only']}
>
	{@render children()}
</svelte:element>
