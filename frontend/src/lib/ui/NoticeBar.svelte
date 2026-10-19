<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';
	import { NOTICE_TONES, type NoticeTone } from './notice';

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'style' | 'children'> {
		tone: NoticeTone;
		/** What it is marked by at its start, in its tone's colour; none for a fact of a file, which is no news. */
		icon?: IconName | undefined;
		/** The bar's test id, which its mark is known by after it. */
		testId: string;
		/** What it says. */
		children: Snippet;
		/** What stands at its far end: what the reader can do about it, and why doing it failed. */
		actions?: Snippet | undefined;
	}

	let { tone, icon, testId, children, actions, ...attributes }: Props = $props();
</script>

<!-- Something the review says, in a bar across what it is about: its mark, its words, and what can be done about
	it at its far end, drawn as its tone says (lib/ui/notice.ts) -->
<div {...attributes} data-testid={testId} class={['cr-ui-notice', NOTICE_TONES[tone]]}>
	{#if icon}
		<span class="cr-ui-notice-mark"><Icon name={icon} size="xs" testId="{testId}-mark" /></span>
	{/if}
	<span class="cr-ui-notice-words">{@render children()}</span>
	{@render actions?.()}
</div>
