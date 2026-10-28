<script lang="ts">
	import type { Snippet } from 'svelte';
	import BreathingDots from './BreathingDots.svelte';
	import { CALLOUT_LOOKS, type CalloutTone } from './callout';
	import Icon from './Icon.svelte';
	import Standing from './Standing.svelte';

	interface Props {
		tone: CalloutTone;
		/** Its first words, said in its tone's colour: what it is, "Reconstructed.". */
		lead: string;
		/** What the agent is doing about what it says, while it does: "The agent is updating the reasons.". */
		underWay?: string | undefined;
		/** Its test id; what is under way is known by this followed by `-under-way`, its dots by `-under-way-dots`. */
		testId: string;
		/** What it says after them. */
		children: Snippet;
		/** Where what it says can be checked, a link: "Read the code that writes it". */
		check?: Snippet | undefined;
	}

	let { tone, lead, underWay, testId, children, check }: Props = $props();

	const drawn = $derived(CALLOUT_LOOKS[tone]);
</script>

<!-- What a part says of itself before what it heads, on its tone's tint (lib/ui/callout.ts) -->
<div data-testid={testId} class={['cr-ui-callout', drawn.look]}>
	<Icon name={drawn.icon} size="sm" tone={drawn.iconTone} />
	<div class="cr-ui-callout-words">
		<p><strong class="cr-ui-callout-lead">{lead}</strong> {@render children()}</p>
		{#if underWay}
			<p class="cr-ui-callout-under-way">
				<Standing tone="agent" stands="on-a-bar" testId="{testId}-under-way"
					><BreathingDots tone="quiet" testId="{testId}-under-way-dots" />{underWay}</Standing
				>
			</p>
		{/if}
		{#if check}
			<p class="cr-ui-callout-check">{@render check()}</p>
		{/if}
	</div>
</div>
