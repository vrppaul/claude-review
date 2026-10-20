<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	/**
	 * How it is drawn:
	 * - box: a setting of a pane, its words first and the browser's own box at the far end of their line, ticked
	 *   in ink as whatever is chosen is; what more is said of it under its words, quieter
	 * - chip: among a header's controls, the whole chip the box to press: the box laid over it unseen, and drawn as
	 *   an icon before its words, ticked once what it marks is done
	 */
	type Drawn = { drawn: 'box'; note?: string | undefined } | { drawn: 'chip'; note?: never };

	type Props = Drawn & {
		/** Whether the choice it stands for is on. */
		checked: boolean;
		/** The test id of its box, which is what is pressed. */
		testId: string;
		/** Called as the reader ticks or unticks it, with whether it is ticked now. */
		onToggle: (checked: boolean) => void;
		/** The words that say the choice, which name its box: a press on them ticks it too. */
		children: Snippet;
	};

	let { drawn, note, checked, testId, onToggle, children }: Props = $props();
</script>

<!-- A choice that is on or off: its words and its box in one label, so the words name the box -->
<!-- The box, seen in a setting's colour, or laid unseen over a chip, which draws its own -->
{#snippet box(drawnAs: string | null)}
	<input
		type="checkbox"
		data-testid={testId}
		class={drawnAs}
		{checked}
		onchange={(event) => onToggle(event.currentTarget.checked)}
	/>
{/snippet}

{#if drawn === 'box'}
	<label class="cr-ui-setting">
		<span>
			{@render children()}
			{#if note}
				<span class="cr-ui-setting-note">{note}</span>
			{/if}
		</span>
		{@render box('cr-ui-checkbox')}
	</label>
{:else}
	<label class="cr-ui-check-chip cr-pressable">
		{@render box(null)}
		<Icon name={checked ? 'ticked' : 'box'} size="xs" />
		{@render children()}
	</label>
{/if}
