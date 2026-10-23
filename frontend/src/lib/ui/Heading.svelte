<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { HEADING_KINDS, HEADING_TONES, type HeadingKind, type HeadingTag, type HeadingTone } from './heading';

	interface HeadingProps extends Omit<HTMLAttributes<HTMLElement>, 'class' | 'style' | 'children'> {
		tag: HeadingTag;
		/** The tone it is said in; the page's own words where it names none. */
		tone?: HeadingTone | undefined;
		/** Whether it is seen, or heard by a screen reader alone where what it heads is seen without it. */
		seen?: boolean;
		testId?: string | undefined;
		/** The heading itself, for whoever hands the keyboard to it. */
		element?: HTMLElement | undefined;
		/** What it says. */
		children: Snippet;
	}

	/**
	 * What it heads, which sets its size and face; and a part's number, where it has one, before its title: a
	 * chapter's. Nothing else a heading heads is numbered.
	 */
	type Numbering = { heads: 'part'; number?: number | undefined } | { heads: HeadingKind; number?: undefined };

	type Props = HeadingProps & Numbering;

	let {
		tag,
		heads,
		tone,
		seen = true,
		testId,
		element = $bindable(),
		number,
		children,
		...attributes
	}: Props = $props();
</script>

<!-- A heading of the page, drawn as what it heads and its tone say: what it is handed besides lands on the
	element, and its test id and look are the library's alone, written after it. A number stands a space before
	what follows it, so the two are read apart: the space between two nodes is kept, where one at the edge of a
	block would be trimmed, so what it says is drawn in each branch -->
<svelte:element
	this={tag}
	bind:this={element}
	{...attributes}
	data-testid={testId}
	class={['cr-ui-heading', HEADING_KINDS[heads], tone && HEADING_TONES[tone], !seen && 'sr-only']}
>
	{#if number === undefined}
		{@render children()}
	{:else}
		<span class="cr-ui-heading-number">{number}</span>
		{@render children()}
	{/if}
</svelte:element>
