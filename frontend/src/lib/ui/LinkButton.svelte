<script lang="ts">
	import type { Snippet } from 'svelte';
	import { buttonLook, type ButtonSize, type ButtonTone } from './button';

	interface Props {
		/** What it is to the reader beside its neighbours, as a button's tone says. */
		tone: ButtonTone;
		size: ButtonSize;
		/** Where it leads, out of the review. */
		href: string;
		/** What the page does as the reader follows it. */
		onfollow: () => void;
		testId: string;
		/** What following it adds, on a chip at its end, where GitHub's Star button keeps its count: "+1". */
		adds?: string | undefined;
		/** The link itself, for whoever hands the keyboard to it: the act a pane leads to, as the pane appears. */
		element?: HTMLAnchorElement | undefined;
		/** What it says. */
		children: Snippet;
	}

	let { tone, size, href, onfollow, testId, adds, element = $bindable(), children }: Props = $props();
</script>

<!-- A way out of the review that is the act a pane leads to: a link, so the browser opens it as one, drawn as the
	button it acts as. It opens in a tab of its own, so the review stays open, and tells the page it opens nothing
	of where it came from -->
<a
	bind:this={element}
	data-testid={testId}
	class={buttonLook(tone, size, false)}
	{href}
	target="_blank"
	rel="noopener noreferrer"
	onclick={onfollow}
>
	{@render children()}{#if adds !== undefined}<span class="cr-ui-button-adds">{adds}</span>{/if}
</a>
