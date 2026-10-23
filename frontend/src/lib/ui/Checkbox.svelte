<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	/**
	 * A setting that hangs on the one above it, drawn as a branch of a tree off that one: locked while it is off,
	 * and what unlocks it said on the pointer.
	 */
	interface Hanging {
		locked: boolean;
		unlocksWith: string;
	}

	/**
	 * How it is drawn:
	 * - box: a setting of a pane, its words first and the page's own box at the far end of their line, ticked
	 *   in ink as whatever is chosen is; what more is said of it under its words, quieter; hanging on the one
	 *   above it, where it does
	 * - chip: among a header's controls, the whole chip the box to press: the box laid over it unseen, and drawn as
	 *   an icon before its words, ticked once what it marks is done
	 */
	type Drawn =
		| { drawn: 'box'; note?: string | undefined; hangs?: Hanging | undefined }
		| { drawn: 'chip'; note?: never; hangs?: never };

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

	let { drawn, note, hangs, checked, testId, onToggle, children }: Props = $props();

	// A setting locked cannot be ticked, and says on the pointer what unlocks it
	const locked = $derived(hangs?.locked ?? false);
</script>

<!-- A choice that is on or off: its words and its box in one label, so the words name the box -->
<!-- The box, seen in a setting's colour, or laid unseen over a chip, which draws its own -->
{#snippet box(drawnAs: string | null)}
	<input
		type="checkbox"
		data-testid={testId}
		class={drawnAs}
		{checked}
		disabled={locked}
		onchange={(event) => onToggle(event.currentTarget.checked)}
	/>
{/snippet}

{#if drawn === 'box'}
	<label
		class={['cr-ui-setting', hangs && 'cr-ui-setting-hanging', locked && 'cr-ui-setting-locked']}
		title={locked ? hangs?.unlocksWith : undefined}
	>
		{#if hangs}
			<!-- Where its branch ends while it is locked: a padlock, which fades as it opens -->
			<span class="cr-ui-setting-lock"><Icon name="locked" size="xs" /></span>
		{/if}
		<span>
			{@render children()}
			{#if note}
				<span class="cr-ui-setting-note">{note}</span>
			{/if}
			<!-- What unlocks it, said to a screen reader with its name as the pointer says it: its box, off, takes no
				keyboard to hear it by -->
			{#if locked}
				<span class="sr-only">{hangs?.unlocksWith}</span>
			{/if}
		</span>
		<!-- The box drawn by the page, and the library's check over it, drawn in as it is ticked -->
		<span class="cr-ui-checkbox">
			{@render box('cr-ui-checkbox-box')}
			<span class="cr-ui-checkbox-check"><Icon name="check" size="xs" /></span>
		</span>
	</label>
{:else}
	<label class="cr-ui-check-chip cr-pressable">
		{@render box(null)}
		<Icon name={checked ? 'ticked' : 'box'} size="xs" />
		{@render children()}
	</label>
{/if}
