<script lang="ts">
	import type { ComponentProps, Snippet } from 'svelte';
	import Row from './Row.svelte';

	/**
	 * When the act at a row's end is in sight:
	 * - always: an act the row offers at all times, as a file folds its names
	 * - while-reached: one seldom taken, in sight while the pointer or the keyboard is on the row, and while what it
	 *   opened stays open
	 */
	type ActShown = 'always' | 'while-reached';

	// The class of each in the library's stylesheet
	const SHOWN: Record<ActShown, string> = {
		always: 'cr-ui-row-act-always',
		'while-reached': 'cr-ui-row-act-while-reached'
	};

	interface Props extends ComponentProps<typeof Row> {
		/**
		 * The act at its end, a control of its own beside the row's one press, never inside it; drawing nothing
		 * while the row has none, so the row stays one element, the keyboard on it, as its act comes and goes.
		 */
		act: Snippet;
		actShown: ActShown;
	}

	let { act, actShown, element = $bindable(), ...row }: Props = $props();
</script>

<!-- A row of a list with an act of its own at its end, where a row that folds draws its chevron: the row is one
	press to where it leads, and a button holds no button, so the act stands beside the row, over its end. The row
	is lit under the pointer while the pointer is on its act too: the two are one row to the eye -->
<div class={['cr-ui-row-with-act', SHOWN[actShown]]}>
	<Row {...row} bind:element />
	<span class="cr-ui-row-act">{@render act()}</span>
</div>
