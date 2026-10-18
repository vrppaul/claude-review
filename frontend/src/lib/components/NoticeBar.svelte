<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import type { IconName } from '$lib/ui/icons';

	interface Props {
		testId: string;
		/**
		 * What kind of thing it says, by its class in the stylesheet: something the reader did or reads
		 * by, in their own colour; the code moving on under them, or a kept draft set aside, each a warning.
		 */
		kind: 'cr-notice-taken' | 'cr-notice-moved' | 'cr-notice-set-aside';
		icon: IconName;
		/** What it says. */
		children: Snippet;
		/** What stands at its far end: what the reader can do about it, and why doing it failed. */
		actions: Snippet;
	}

	let { testId, kind, icon, children, actions }: Props = $props();
</script>

<!-- Something the review says of itself, a bar across the page above what is read, so it stands however
	far down the reader is: an icon, its words, and what can be done about it at its far end -->
<div
	data-testid={testId}
	class={['cr-notice', kind, 'flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs']}
>
	<span class="cr-notice-mark"><Icon name={icon} size="xs" /></span>
	<span>{@render children()}</span>
	<div class="flex-1"></div>
	{@render actions()}
</div>
