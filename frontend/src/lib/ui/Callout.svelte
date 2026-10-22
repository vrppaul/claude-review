<script lang="ts">
	import type { Snippet } from 'svelte';
	import { CALLOUT_LOOKS, type CalloutTone } from './callout';
	import Icon from './Icon.svelte';

	interface Props {
		tone: CalloutTone;
		/** Its first words, said in its tone's colour: what it is, "Reconstructed.". */
		lead: string;
		testId: string;
		/** What it says after them. */
		children: Snippet;
	}

	let { tone, lead, testId, children }: Props = $props();

	const drawn = $derived(CALLOUT_LOOKS[tone]);
</script>

<!-- What a part says of itself before what it heads, on its tone's tint (lib/ui/callout.ts) -->
<div data-testid={testId} class={['cr-ui-callout', drawn.look]}>
	<Icon name={drawn.icon} size="sm" tone={drawn.iconTone} />
	<p><strong class="cr-ui-callout-lead">{lead}</strong> {@render children()}</p>
</div>
