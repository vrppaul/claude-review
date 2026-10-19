<script lang="ts">
	import Heading from './Heading.svelte';
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';
	import type { PaneHead } from './pane';

	interface Props {
		head: PaneHead;
		/** The pane's test id, which its heading and its close are known by after it. */
		testId: string;
	}

	let { head, testId }: Props = $props();
</script>

<!-- What heads a pane, the same in every pane that has a head: what it is called, at the one size a pane's
	heading has, what stands beside that, and at the far end the way to put the pane away -->
<header class="cr-ui-pane-head">
	<Heading tag="h2" heads="pane" testId="{testId}-heading">{head.heading}</Heading>
	{@render head.aside?.()}
	<IconButton
		tone="quiet"
		size="xs"
		label={head.closing ?? `Close ${head.heading}`}
		testId="{testId}-close"
		onclick={head.close}
	>
		<Icon name="cross" size="xs" />
	</IconButton>
</header>
