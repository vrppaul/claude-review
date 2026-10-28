<script lang="ts">
	import type { Snippet } from 'svelte';
	import { CHIP_NAMES, CHIP_VOICES, type ChipReach, type PartChipReach } from './chip';
	import Icon from './Icon.svelte';
	import type { Voice } from './voice';

	/**
	 * What it names, and what it does: a thread's place or a file, in any reach; a chapter, only as a way to it; a
	 * part of the page, taken out by its cross or only named.
	 */
	type Naming =
		| ({ names: 'place' } & ChipReach)
		| { names: 'chapter'; onclick: () => void }
		| ({ names: 'part' } & PartChipReach);

	type Props = Naming & {
		/** Whose words named it. */
		voice: Voice;
		/** What it names in full, shown under the pointer, where its words are short of that. */
		title?: string | undefined;
		/** Its test id; its cross, where it has one, is known by this followed by `-remove`. */
		testId: string;
		/** What it names. */
		children: Snippet;
	};

	let { voice, names, title, testId, children, ...reach }: Props = $props();

	const drawn = $derived(['cr-ui-chip', CHIP_VOICES[voice], CHIP_NAMES[names]]);
</script>

<!-- What it names, on one line, cut where the room it stands in ends -->
{#snippet words()}
	<span class="cr-ui-chip-words">{@render children()}</span>
{/snippet}

<!-- A thread, a file or a chapter named, in the colour of whoever named it (lib/ui/chip.ts) -->
{#if 'onclick' in reach}
	<button type="button" data-testid={testId} {title} class={[drawn, 'cr-pressable']} onclick={reach.onclick}>
		{@render words()}
	</button>
{:else if 'onRemove' in reach}
	<span data-testid={testId} {title} class={drawn}>
		{@render words()}
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
{:else if 'outOfReach' in reach}
	<span data-testid={testId} {title} class={[drawn, 'cr-ui-chip-out-of-reach']}>
		{@render words()}
	</span>
{:else}
	<span data-testid={testId} {title} class={drawn}>
		{@render words()}
	</span>
{/if}
