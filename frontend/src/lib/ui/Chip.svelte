<script lang="ts">
	import type { Snippet } from 'svelte';
	import { CHIP_VOICES, type ChipReach, type ChipVoice } from './chip';
	import Icon from './Icon.svelte';

	type Props = ChipReach & {
		voice: ChipVoice;
		/** What it names in full, shown under the pointer, where its words are short of that. */
		title?: string | undefined;
		/** Its test id; its cross, where it has one, is known by this followed by `-remove`. */
		testId: string;
		/** What it names. */
		children: Snippet;
	};

	let { voice, title, testId, children, ...reach }: Props = $props();
</script>

<!-- A thread or a file named in what is said, in the colour of whoever named it (lib/ui/chip.ts) -->
{#if 'onclick' in reach}
	<button
		type="button"
		data-testid={testId}
		{title}
		class={['cr-ui-chip cr-pressable', CHIP_VOICES[voice]]}
		onclick={reach.onclick}
	>
		{@render children()}
	</button>
{:else if 'onRemove' in reach}
	<span data-testid={testId} {title} class={['cr-ui-chip', CHIP_VOICES[voice]]}>
		{@render children()}
		<button
			type="button"
			data-testid="{testId}-remove"
			class="cr-ui-chip-remove cr-pressable"
			aria-label={reach.removing}
			title={reach.removing}
			onclick={reach.onRemove}
		>
			<Icon name="cross" size="xs" />
		</button>
	</span>
{:else}
	<span data-testid={testId} {title} class={['cr-ui-chip cr-ui-chip-out-of-reach', CHIP_VOICES[voice]]}>
		{@render children()}
	</span>
{/if}
